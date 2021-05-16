import math
from dataclasses import dataclass
from utils import *
from settings import *
import json
from typing import List, Dict, Tuple


def mute_mask_repr(mask):
    reprs = []

    i = 0
    for instrument in reversed(RANDOM_SONG_INSTRUMENT_SETTINGS):
        num_cs = 2 * instrument.num_cps

        instrument_mask = (mask & (((1 << num_cs) - 1) << i)) >> i
        i += num_cs

        reprs.append(bin(instrument_mask)[2:].zfill(num_cs))
    
    return "_".join(reversed(reprs))


def blank_wheel(num_channels: int, num_beats: int) -> List[List[int]]:
    song: List[List[int]] = [[0]*num_beats]*num_channels
    song = list(map(list, song))  # Make all the lists truly independent
    return song


def get_random_note_counts(num_cs: int, npb: float, ratio: float):
    notes_per_cycle = npb * BEATS_PER_WHEEL

    c_weights: List[float] = [
        randf(1, ratio) for c in range(num_cs)]
    t_weight: float = sum(c_weights)
    c_counts: List[int] = [math.floor(
        (weight/t_weight)*notes_per_cycle) for weight in c_weights]

    return c_counts


def make_highres_wheel_from_counts(c_counts: List[int]):
    wheel = blank_wheel(len(c_counts), BEATS_PER_WHEEL*RANDOM_SONG_WRITING_RESOLUTION)
    for c in range(len(c_counts)):
        # A probably very slow way of finding places for new notes:
        remaining_points = list(range(BEATS_PER_WHEEL*RANDOM_SONG_WRITING_RESOLUTION))
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
        for i in range(BEATS_PER_WHEEL):
            wheel[-1].append(sum(line[(i*RANDOM_SONG_WRITING_RESOLUTION):((i+1)*RANDOM_SONG_WRITING_RESOLUTION)]))
    return wheel

def wheel_to_text(wheel):
    for c_notes in wheel:
        yield "".join([str(notes) if notes > 0 else "-" for notes in c_notes])

def wheel_from_text(wheel_text: List[str], num_channels=NUM_CHANNELS, num_beats=BEATS_PER_WHEEL):
    wheel = blank_wheel(num_channels, num_beats)
    for i, line in enumerate(wheel_text):
        for j, char in enumerate(line):
            wheel[i][j] = 0 if char == "-" else int(char)
    return wheel


class MMXSong:
    def __init__(self, wheel, mute_instructions):
        self.wheel: List[List[int]] = wheel
        self.mute_instructions: List[SongMuteInstruction] = mute_instructions
        self.mute_masks: List[Tuple[int, int, str]] = []

        beat_count = 0
        for i, mute_instruction in enumerate(self.mute_instructions):
            # Expand the instruction mask into a full mask
            mask = 0
            for j, MUTE_GROUP in enumerate(MUTE_GROUPS):
                if mute_instruction.mask & (1 << j):
                    mask |= MUTE_GROUP
            self.mute_masks.append((mask, beat_count, mute_instruction.length, mute_instruction.name))
            beat_count += mute_instruction.length
        self.beat_count = beat_count
        
        # WARNING: Caching
        self.__cached_notes = [None for i in range(self.beat_count)]

        self.note_count = 0
        for i in range(self.beat_count):
            self.note_count += len(list(self.notes_on_beat(i)))
        self.npb = self.note_count / self.beat_count


    def is_unmuted_on_beat(self, i, channel):
        i %= self.beat_count

        for x, (mute_mask, start_beat, length, *_) in enumerate(self.mute_masks):
            if start_beat <= i < start_beat + length:
                return not not (mute_mask & (1 << (NUM_CHANNELS - 1 - channel)))


    def notes_on_beat(self, i):
        i %= self.beat_count

        # WARNING: Caching
        if self.__cached_notes[i] is not None:
            for c in self.__cached_notes[i]:
                yield c
            return
        self.__cached_notes[i] = []
        for c in range(NUM_CHANNELS):
            if self.is_unmuted_on_beat(i, c):
                for _ in range(self.wheel[c][i % BEATS_PER_WHEEL]):
                    self.__cached_notes[i].append(c)
                    yield c
    
    @staticmethod
    def make_random():
        wheel = []
        for instrument in RANDOM_SONG_INSTRUMENT_SETTINGS:
            instrument_cp_counts = get_random_note_counts(instrument.num_cps, instrument.npb/2, instrument.ratio)
            # Make a wheel for both channels in each pair
            # (so that min dist between notes requirement is definitely upheld)
            highres_wheel1 = make_highres_wheel_from_counts(instrument_cp_counts)
            highres_wheel2 = make_highres_wheel_from_counts(instrument_cp_counts)

            highres_wheel_merged = [[(x1+x2) for (x1,x2) in zip(line1, line2)] for (line1, line2) in zip(highres_wheel1, highres_wheel2)]
            
            highres_wheel = blank_wheel(instrument.num_cps*2, BEATS_PER_WHEEL*RANDOM_SONG_WRITING_RESOLUTION)
            for cp in range(instrument.num_cps):
                total = 0
                for i in range(BEATS_PER_WHEEL*RANDOM_SONG_WRITING_RESOLUTION):
                    for x in range(highres_wheel_merged[cp][i]):
                        highres_wheel[2*cp + (total % 2)][i] += 1
                        total += 1
            wheel += compress_wheel(highres_wheel)
        
        return MMXSong(wheel, RANDOM_SONG_MUTE_INSTRUCTIONS)

    @staticmethod
    def from_json(json_str):
        data = json.loads(json_str)

        wheel = wheel_from_text(data["wheel"])
        
        mute_instructions = []
        for (mask_str, length, name) in data["mute_instructions"]:
            mask = 0
            if mask_str.startswith("0b"):
                mask = int(mask_str, base=0)
            else:
                mask = int(mask_str, base=2)
            mute_instructions.append(SongMuteInstruction(mask, length, name))

        return MMXSong(wheel, mute_instructions)

    @staticmethod
    def from_file(json_fp):
        with open(json_fp, "r") as f:
            json_str = f.read()
        return MMXSong.from_json(json_str)

    def to_json(self):
        data = {
            "wheel": wheel_to_text(self.wheel),
            "mute_instructions": [(mi.mask, mi.length, mi.name) for mi in self.mute_instructions]
        }
        return json.dumps(data)

    def to_file(self, json_fp):
        json_str = self.to_json()
        with open(json_fp, "w") as f:
            json_str = f.write(json_str)

    def __repr__(self):
        return (
            "Wheel:\n" + 
            "\n".join(f"{i+1:02d} {c_text} {sum(c_notes)}" for i, (c_notes, c_text) in enumerate(zip(self.wheel, wheel_to_text(self.wheel))))
            + "\n\n" +
            "Mute Masks:\n" + 
            "\n".join([str((mute_mask_repr(mask), start_beat, length, name)) for (mask, start_beat, length, name) in self.mute_masks])
            + "\n\n" + 
            "Notes Count:        {0}\n".format(self.note_count) +
            "Beats Length:       {0}\n".format(self.beat_count) +
            "Notes per Beat:     {0:.2f}\n".format(self.npb) + 
            "Max Notes per Beat: {0:.2f}\n".format(sum(map(sum, self.wheel)) / BEATS_PER_WHEEL)
        )
        

if __name__ == "__main__":
    if SONG_PATH == None:
        print(repr(MMXSong.make_random()))
    else:
        print(repr(MMXSong.from_file(SONG_PATH)))