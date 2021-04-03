from dataclasses import dataclass
import random
import math

from song import *
from utils import *

# How many marbles are in the pipe from the divider to gate?
MAX_MARBLES_PER_CHANNEL: int = 32
# How many channels are there?
NUM_CHANNELS: int = 38
# How many crank turns does it take to fully rotate the drum?
NUM_CRANK_TURNS: int = 64

# The maximum number of marbles per crank turn that would be programmed for
#     (NOT how many can be carried up by the lifts)
MARBLES_PER_CRANK_TURN = 7.2

# How many more times will the most played channel play vs the least?
CHANNEL_MINMAX_WEIGHT = 20

# The probability that a marble going past an empty channel in the divider will fall in
# This is probably random depending the marble height of that specific channel or neighbouring channels, 
# so I give each channel a random value between these two (uniformly)
CHANNEL_ACCEPT_PROB_MIN = 0.4
CHANNEL_ACCEPT_PROB_MAX = 0.8

# How many times will the crank need to be turned before a dropped marble gets back to the top of the divider
# The conveyor is at least 13 by itself, then you have the ring lifts and the marbles rolling from the drops to the lifts
CRANK_TURNS_UNTIL_MARBLE_RETURN = 24
# Same as above but for marble recycle by fishstair
CRANK_TURNS_UNTIL_MARBLE_RECYCLE = 8

# ----- Conveyor settings -----
CONVEYOR_NUM_CHANNELS = 8
CONVEYOR_CHANNEL_ACCEPT_PROB = 0.92
# Where do the first and last marble lanes enter the divider?
CONVEYOR_DIVIDER_ENTRY_START = 4
CONVEYOR_DIVIDER_ENTRY_END = NUM_CHANNELS - 10
# How many marbles can be waiting for the conveyor?
CONVEYOR_RESERVOIR_CAPACITY = 40
# Initial marbles will end up just getting dumped into the fishstair pool so this is a bit redundant
CONVEYOR_RESERVOIR_INITIAL = 0

# ----- FISHSTAIR settings -----
FISHSTAIR_NUM_CHANNELS = 4
FISHSTAIR_CHANNEL_ACCEPT_PROB = 0.95
# The fishstair goes straight on at the start of the divider
FISHSTAIR_DIVIDER_ENTRY = 0
# How many marbles can be waiting for the conveyor? 
FISHSTAIR_RESERVOIR_CAPACITY = 4*100
# !!!! This seems important: !!!!
FISHSTAIR_RESERVOIR_INITIAL = 4*80

# How many marbles to drop before we give up trying to break the MMX?
LONG_RUN_MARBLE_GOAL = 1_000_000


# Compute conveyor belt entry points assuming uniform spread
CONVEYOR_CHANNEL_ENTRY_POINTS = [
    int(CONVEYOR_DIVIDER_ENTRY_START + 
        (CONVEYOR_DIVIDER_ENTRY_END-CONVEYOR_DIVIDER_ENTRY_START)*(i/(CONVEYOR_NUM_CHANNELS-1)))
    for i in range(CONVEYOR_NUM_CHANNELS)
]

# Make the song

#SONG = make_song(NUM_CHANNELS, NUM_CRANK_TURNS, MARBLES_PER_CRANK_TURN * NUM_CRANK_TURNS, CHANNEL_MINMAX_WEIGHT)
#SONG = make_song_channels_paired_sectioned(int(NUM_CHANNELS/2), NUM_CRANK_TURNS, MARBLES_PER_CRANK_TURN * NUM_CRANK_TURNS, CHANNEL_MINMAX_WEIGHT)

NUM_SECTIONS = 2
SONG = make_song_channels_paired_sectioned(
    int(NUM_CHANNELS/2), 
    NUM_SECTIONS, 
    int(NUM_CRANK_TURNS/NUM_SECTIONS), 
    int(MARBLES_PER_CRANK_TURN * NUM_CRANK_TURNS / NUM_SECTIONS), 
    CHANNEL_MINMAX_WEIGHT
)

print("Notes per channel:", list(map(sum, SONG)))
print("Num notes in song:", sum(map(sum, SONG)))
print("MAX MARBLES_PER_SONG:", MARBLES_PER_CRANK_TURN * NUM_CRANK_TURNS)

with open("song.txt", "w") as f:
    f.write(song_repr(SONG))



@dataclass
class Channel:
    index: int
    marble_accept_p: float
    count: int = MAX_MARBLES_PER_CHANNEL
    max_count: int = MAX_MARBLES_PER_CHANNEL

class MMX:
    def __init__(self):
        self.channels: list[Channel] = [Channel(i, randf(CHANNEL_ACCEPT_PROB_MIN, CHANNEL_ACCEPT_PROB_MAX)) for i in range(NUM_CHANNELS)]
        self.fishstair_waiting = FISHSTAIR_RESERVOIR_INITIAL
        self.conveyor_waiting = CONVEYOR_RESERVOIR_INITIAL

        self.return_queue = [0] * CRANK_TURNS_UNTIL_MARBLE_RETURN
        self.recycle_queue = [0] * CRANK_TURNS_UNTIL_MARBLE_RECYCLE

        self.song_i = 0

    def divide_marble(self, start: int):
        for c in range(start, NUM_CHANNELS):
            if self.channels[c].count >= self.channels[c].max_count:
                continue
            if bernoulli(self.channels[c].marble_accept_p):
                self.channels[c].count += 1
                return
        self.recycle_queue[-1] += 1

    def simul_step(self):
        # Return and recycle queues moves forward
        self.conveyor_waiting += self.return_queue[0]
        self.return_queue = self.return_queue[1:] + [0]

        self.fishstair_waiting += self.recycle_queue[0]
        self.recycle_queue = self.recycle_queue[1:] + [0]

        # Redistribute Marbles
        for conveyor_c in range(CONVEYOR_NUM_CHANNELS):
            if self.conveyor_waiting <= 0:
                continue
            
            if bernoulli(CONVEYOR_CHANNEL_ACCEPT_PROB):
                self.conveyor_waiting -= 1
                self.divide_marble(CONVEYOR_CHANNEL_ENTRY_POINTS[conveyor_c])

        # Fishstair only adds to the divider every other beat
        if (self.song_i % 2) == 0:
            for fishstair_c in range(FISHSTAIR_NUM_CHANNELS):
                if self.fishstair_waiting <= 0:
                    continue
                
                if bernoulli(FISHSTAIR_CHANNEL_ACCEPT_PROB):
                    self.fishstair_waiting -= 1
                    self.divide_marble(FISHSTAIR_DIVIDER_ENTRY)

        # Play Notes
        num_played = 0
        played_empty = False
        fishstair_overflowed = self.fishstair_waiting > FISHSTAIR_RESERVOIR_CAPACITY
        conveyor_overflowed = self.conveyor_waiting > CONVEYOR_RESERVOIR_CAPACITY

        for c in range(NUM_CHANNELS):
            if SONG[c][self.song_i]:
                if self.channels[c].count <= 0:
                    print("Fired an empty channel")
                    played_empty = True
                    continue
                self.channels[c].count -= 1
                self.return_queue[-1] += 1
                num_played += 1                
        
        self.song_i = (self.song_i + 1) % NUM_CRANK_TURNS

        return num_played, played_empty, fishstair_overflowed, conveyor_overflowed
    
    def __repr__(self):
        return "MMX [\n    Channels: [{0}], \n    Return Queue: [{1}], \n    Conveyor Waiting: {2}, \n    Recycle Queue: [{3}], \n    Fishstair Waiting: {4}\n]".format(
            ", ".join(str(channel.count) for channel in self.channels),
            ", ".join(map(str, self.return_queue)),
            self.conveyor_waiting,
            ", ".join(map(str, self.recycle_queue)),
            self.fishstair_waiting
        )


if __name__ == "__main__":
    mmx = MMX()
    num_played = 0
    ran_dry = False

    print()

    while num_played <= LONG_RUN_MARBLE_GOAL:
        num_played_incr, played_empty, fishstair_overflowed, conveyor_overflowed = mmx.simul_step()
        if played_empty:
            print("Ran dry after {0} marbles dropped".format(num_played))
            ran_dry = True
            break
        if fishstair_overflowed:
            print("Fishstair overflowed after {0} marbles dropped".format(num_played))
        if conveyor_overflowed:
            print("Conveyor overflowed after {0} marbles dropped".format(num_played))
        num_played += num_played_incr
    
    if not ran_dry:
        print("Never ran dry")
    print()
    print(repr(mmx))

