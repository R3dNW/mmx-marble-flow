import math
from dataclasses import dataclass
from utils import *
from constants import *
from namespace import NAMESPACE


# Instrument notes per beat to use when creating random songs
# From here: https://www.youtube.com/watch?v=5ZBb0jidgwQ 
# (Very old but I don't think there's any newer info)
# INSTRUMENT_NPBS = [
#     (4,     "VIBRAPHONE"),
#     (4/64,  "CYMBAL"), # Not played too often??????
#     (11/4,  "DRUMS"),
#     (16/4,  "BASS") # I couldn't get a good look at this so I'm guessing
# ]
INSTRUMENT_NPBS = [
    (4,   "VIBRAPHONE"),
    (2/64,  "CYMBAL"),
    (3,   "DRUMS"),
    (3,  "BASS")
]

# What is the ratio between least and most played channel (pairs) in this instrument group
# to use when creating random songs. I'm just guessing based on nothing much.
INSTRUMENT_RATIOS = {
    (10,    "VIBRAPHONE"),
    (1,     "CYMBAL"),
    (3,     "DRUMS"),
    (3,     "BASS")
}

# I saw somewhere that 3/16 of a bar is the min timing between two notes on the same channel
SONG_WRITING_RESOLUTION = 4 # How many divisions of a beat to consider when making random music
MIN_DISTANCE_BETWEEN_NOTES = 3 # How many of the smallest divisions at a minimum between notes


MUTE_GROUPS = list(map(lambda x: x[0], reversed([
    (0b1111111111111111111111_00_00_00_00_00000000, "Vibraphone"),
    (0b0000000000000000000000_11_00_00_00_00000000, "Cymbal"),
    (0b0000000000000000000000_00_11_00_00_00000000, "Kick Drum"),
    (0b0000000000000000000000_00_00_11_00_00000000, "Snare Drum"),
    (0b0000000000000000000000_00_00_00_11_00000000, "Hi-hat"),
    (0b0000000000000000000000_00_00_00_00_11111111, "Bass")
])))
NUM_MUTE_GROUPS = len(MUTE_GROUPS)

# From original marble machine, just me guessing
# STANDARD_MUTE_GROUP_LIST = [    
#     # This is important, the machine will have to be rotated between songs so it gets a chance to reset
#     (0b000000, 64, "Load song"),
    
#     (0b000000, 32, "Wind Up"),

#     (0b100000, 32, "Vibraphone Intro"),
#     (0b100100, 32, "Add Snare"),
#     (0b111111, 64, "'Verse' 1"),
#     (0b111111, 64, "'Verse' 2"),
    
#     # Marbles are dropped here and that should probably be counted, 
#     # but I doubt every song will have this so I won't put the work into implementing marble drops during a pause
#     (0b000000, 0, "Brakedown"),
    
#     (0b000001, 16, "Bass Wind Up"),
#     (0b000101, 16, "Bass & Snare"),
#     (0b000101, 32, "Bass & Snare & Kick"),
#     (0b111111, 64, "'Verse' 3"),
#     (0b111111, 64, "'Verse' 4"),
# ]

# A custom setup that works slightly better
STANDARD_MUTE_GROUP_LIST = [    
    # This is important, the machine will have to be rotated between songs so it gets a chance to reset
    (0b000000, 96, "Load song"),
    
    (0b000000, 32, "Wind Up"),

    (0b100000, 32, "Vibraphone Intro"),
    (0b100100, 32, "Add Snare"),
    (0b111111, 64, "Full MMX"),
    (0b000001, 32, "Bass Solo"),
    (0b000101, 32, "Bass & Snare"),
    (0b000101, 64, "Bass & Snare & Kick"),
    (0b111111, 64, "Full MMX"),
    (0b111110, 64, "Drop Bass"),
]


def mute_mask_repr(mask):
    reprs = []

    i = 0
    for (num_cps, *_) in INSTRUMENT_CHANNEL_PAIRS:
        num_cs = 2 * num_cps

        instrument_mask = (mask & (((1 << num_cs) - 1) << i)) >> i
        i += num_cs

        reprs.append(bin(instrument_mask)[2:].zfill(num_cs))
    
    return "_".join(reprs)



def blank_wheel(num_channels: int, num_beats: int) -> list[list[bool]]:
    song: list[list[int]] = [[0]*num_beats]*num_channels
    song = list(map(list, song))  # Make all the lists truly independent
    return song


def get_random_note_counts(num_cs: int, npb: float, ratio: float):
    notes_per_cycle = npb * BEATS_PER_CYCLE

    c_weights: list[float] = [
        randf(1, ratio) for c in range(num_cs)]
    t_weight: float = sum(c_weights)
    c_counts: list[int] = [math.floor(
        (weight/t_weight)*notes_per_cycle) for weight in c_weights]

    return c_counts


def make_highres_wheel_from_counts(c_counts: list[int]):
    wheel = blank_wheel(len(c_counts), BEATS_PER_CYCLE*SONG_WRITING_RESOLUTION)
    for c in range(len(c_counts)):
        # A probably very slow way of finding places for new notes:
        remaining_points = list(range(BEATS_PER_CYCLE*SONG_WRITING_RESOLUTION))
        for _ in range(c_counts[c]):
            i = remaining_points[random.randrange(len(remaining_points))]
            for j in range(i-MIN_DISTANCE_BETWEEN_NOTES+1, i+MIN_DISTANCE_BETWEEN_NOTES):
                if j in remaining_points:
                    remaining_points.remove(j)
            wheel[c][i] = 1
    
    return wheel


# Compress a wheel from song writing to simulation resolution
def compress_wheel(highres_wheel):
    wheel = []
    for line in highres_wheel:
        wheel.append([])
        for i in range(BEATS_PER_CYCLE):
            wheel[-1].append(sum(line[(i*SONG_WRITING_RESOLUTION):((i+1)*SONG_WRITING_RESOLUTION)]))
    return wheel


class MMXSong:
    def __init__(self, wheel, mute_groups_list):
        self.wheel: list[list[int]] = wheel
        self.mute_groups_list: list[tuple[int, int]] = mute_groups_list
        
        self.mute_masks: list[tuple[int, int]] = []

        beat_count = 0
        for i, mute_groups in enumerate(self.mute_groups_list):
            mask = 0
            for j, MUTE_GROUP in enumerate(MUTE_GROUPS):
                if mute_groups[0] & (1 << j):
                    mask |= MUTE_GROUP
            self.mute_masks.append((mask, beat_count, *mute_groups[2:]))
            beat_count += mute_groups[1]
        self.beat_count = beat_count

        self.note_count = 0
        for i in range(self.beat_count):
            self.note_count += len(list(self.notes_on_beat(i)))
        self.npb = self.note_count / self.beat_count

    def is_unmuted_on_beat(self, i, channel):
        i %= self.beat_count

        for x, (mute_mask, start_beat, *_) in enumerate(self.mute_masks):
            if start_beat <= i < (self.mute_masks[x+1][1] if (x+1) < len(self.mute_masks) else self.beat_count):
                return not not (mute_mask & (1 << channel))

    def notes_on_beat(self, i):
        i %= self.beat_count

        for c in range(NUM_CHANNELS):
            if self.is_unmuted_on_beat(i, c):
                for _ in range(self.wheel[c][i % BEATS_PER_CYCLE]):
                    yield c
    
    @staticmethod
    def make_random():
        wheel = []
        for (num_cps, _), (npb, _), (ratio, _) in zip(INSTRUMENT_CHANNEL_PAIRS, INSTRUMENT_NPBS, INSTRUMENT_RATIOS):
            instrument_cp_counts = get_random_note_counts(num_cps, npb/2, ratio)
            # Make a wheel for each channel (so that min dist between notes requirement is definitely upheld)
            highres_wheel1 = make_highres_wheel_from_counts(instrument_cp_counts)
            highres_wheel2 = make_highres_wheel_from_counts(instrument_cp_counts)

            highres_wheel_merged = [[(x1+x2) for (x1,x2) in zip(line1, line2)] for (line1, line2) in zip(highres_wheel1, highres_wheel2)]
            
            highres_wheel = blank_wheel(num_cps*2, BEATS_PER_CYCLE*SONG_WRITING_RESOLUTION)
            for cp in range(num_cps):
                total = 0
                for i in range(BEATS_PER_CYCLE*SONG_WRITING_RESOLUTION):
                    for x in range(highres_wheel_merged[cp][i]):
                        highres_wheel[2*cp + (total % 2)][i] += 1
                        total += 1
            wheel += compress_wheel(highres_wheel)
        
        return MMXSong(wheel, STANDARD_MUTE_GROUP_LIST)
    
    def __repr__(self):
        return (
            "Wheel:\n" + 
            "\n".join(('{:02d}'.format(i+1) + " " + "".join([str(notes) if notes > 0 else "-" for notes in c_notes]) + " " + (str(sum(c_notes)))) for i, c_notes in enumerate(self.wheel))
            + "\n\n" +
            "Mute Groups:\n" + 
            "\n".join([str((mute_mask_repr(mask), length, *args)) for (mask, length, *args) in self.mute_masks])
            + "\n\n" + 
            "Notes Count:        {0}\n".format(self.note_count) +
            "Beats Length:       {0}\n".format(self.beat_count) +
            "Notes per Beat:     {0:.2f}\n".format(self.npb) + 
            "Max Notes per Beat: {0:.2f}\n".format(sum(map(sum, self.wheel)) / BEATS_PER_CYCLE)
        )
        

if __name__ == "__main__":
    print(repr(MMXSong.make_random()))
