from settings_structures import *

# ----- BASIC SETTINGS (probably don't change) -----
NUM_CHANNEL_PAIRS = 19
NUM_CHANNELS = NUM_CHANNEL_PAIRS * 2
BEATS_PER_WHEEL = 64

MUTE_GROUPS = list(map(lambda x: x[0], reversed([
    (0b1111111111111111111111_00_00_00_00_00000000, "Vibraphone"),
    (0b0000000000000000000000_11_00_00_00_00000000, "Cymbal"),
    (0b0000000000000000000000_00_11_00_00_00000000, "Kick Drum"),
    (0b0000000000000000000000_00_00_11_00_00000000, "Snare Drum"),
    (0b0000000000000000000000_00_00_00_11_00000000, "Hi-hat"),
    (0b0000000000000000000000_00_00_00_00_11111111, "Bass")
])))
NUM_MUTE_GROUPS = len(MUTE_GROUPS)

# -----  SETTINGS TO PLAY WITH -----

# Path to a JSON file describing an MMX song, or None for a random song
SONG_PATH = "song.json"

# How many marbles to try and drop?
LONG_RUN_MARBLE_GOAL = 1_000_000
# How often to issue reports about progress?
REPORT_COUNT = 20

# Display plots using matplotlib?
DO_PLOTTING = True

# How many marbles are in the pipe from the divider to gate?
MAX_MARBLES_PER_CHANNEL = 32


# The probability that a marble going past an empty channel in the divider will fall in
# This is probably random depending the marble height of that specific channel or neighbouring channels, 
# so I give each channel a random value between these two (uniformly)
CHANNEL_ACCEPT_PROB_MIN = 0.4
CHANNEL_ACCEPT_PROB_MAX = 0.8


# Try flipping the divider direction to see if it improves things
# This seems to make things worse if anything as it means that the bass is only fed by 
# the two marbles per beat of the fishstair, and nothing else.
REVERSE_DIVIDER = False


# Marble return, i.e. marbles from drop to return to divider
# As I understand it the key bottleneck here should be the conveyor so that is what we simulate,
#     and we just assume everything else works as expected.
MARBLE_RETURN_SETTINGS = MarbleTransportSettings(
    num_channels=8,

    channel_accept_p=15/16,     # How likely is it each channel of the conveyor picks up a marble?

    beats_per_release=1,        # The conveyor runs every beat

                                # The number of beats it takes for a marble to go from dropper to divider
    beats_to_transport=48,      # Because the model doesn't account for time on the divider, this should also be included here

    divider_entry_start=4,      # Assume that the marble lanes put marbles onto the divider at even
    divider_entry_end=38-10,    # intervals between these 2 divider channels

    reservoir_capacity=40,      # How many marbles can be held waiting for the conveyor?
    reservoir_initial=0,        # How many marbles start waiting for the conveyor?
)

# Marble recycle, i.e. marbles from end of divider back to divider
# As I understand it the key bottleneck here should be the fishstair
MARBLE_RECYCLE_SETTINGS = MarbleTransportSettings(
    num_channels=4,

                                # How likely is it each channel of the fishstair picks up a marble?
    channel_accept_p=0.9999,    # With a strong db4, the buffer, and solved pinch, this should be very reliable 

    beats_per_release=2,        # The fishstair runs every other beat

                                # The number of beats it takes for a marble to go from end of divider to back onto divider
    beats_to_transport=16,      # Because the model doesn't account for time on the divider, this should also be included here

    divider_entry_start=0,      # Assume that the marble lanes put marbles onto the divider at even
    divider_entry_end=0,        # intervals between these 2 divider channels

    reservoir_capacity=4*70,   # How many marbles can be held waiting for the fishstair?
    reservoir_initial=4*60,     # How many marbles start waiting for the fishstair?
)


# Old reference video: https://www.youtube.com/watch?v=5ZBb0jidgwQ
# TODO: Could also refer to the original marble machine and scale up by how much more capable MMX should ideally be

# Settings used when creating random programming wheels to test
RANDOM_SONG_INSTRUMENT_SETTINGS = [
    # (<Number of Channel Pairs>, <Notes per beat>, <Max ratio of notes played between least and most played channels>, <Name of instrument>)
    InstrumentSettings(11, 4,    10, "Vibraphone"),
    InstrumentSettings(1,  2/64, 1,  "Cymbal"),
    InstrumentSettings(3,  2,    3,  "Drums"),
    InstrumentSettings(4,  2,    3,  "Bass")
]

# But an MMX song is _more_ than what is programmed onto the wheel:
# When playing a concert, the various mute groups of the MMX will be muted and unmuted a lot:
RANDOM_SONG_MUTE_INSTRUCTIONS = [
    # (<MuteMask>, <Length of section in beats>, <Name of section>)

    # The MuteMask is a binary mask where 1 means the instrument is playing and 0 means it is muted
    # These groups are in left to right order across the machine so (if I'm correct):
    # Vibraphone, Cymbal, Kick drum, Snare drum, Hi-hat, Bass

    # See MUTE_GROUPS variable.

    # DISCLAIMER: I have no idea how to structure a song

    SongMuteInstruction(0b000000, 64, "Load song"),

    SongMuteInstruction(0b000000, 32, "Wind Up"),

    SongMuteInstruction(0b100000, 32, "Vibraphone Intro"),
    SongMuteInstruction(0b100100, 32, "Add Snare"),
    SongMuteInstruction(0b111111, 64, "Full MMX"),
    SongMuteInstruction(0b000001, 32, "Bass Solo"),
    SongMuteInstruction(0b000101, 32, "Bass & Snare"),
    SongMuteInstruction(0b001101, 64, "Bass & Snare & Kick"),
    SongMuteInstruction(0b111111, 64, "Full MMX"),
    SongMuteInstruction(0b111110, 64, "Drop Bass"),

    SongMuteInstruction(0b000000, 32, "Wind Down")
]

# I *think* this is what the original marble machine used, but I'm only guessing
# RANDOM_SONG_MUTE_INSTRUCTIONS = [
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

# I saw somewhere that 3/16 of a bar (3/4 of a note) is the min timing between two notes on the same channel
# How many divisions of a beat to consider when making random music
RANDOM_SONG_WRITING_RESOLUTION = 4
# How many of these smallest divisions at a minimum between notes
MIN_DISTANCE_BETWEEN_NOTES = 3


