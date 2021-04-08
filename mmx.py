from dataclasses import dataclass
import random
import math

from constants import *
from song import MMXSong
from utils import *


DO_PLOTTING = False
if DO_PLOTTING:
    import matplotlib.pyplot as plt


# How many marbles are in the pipe from the divider to gate?
MAX_MARBLES_PER_CHANNEL: int = 40

# The probability that a marble going past an empty channel in the divider will fall in
# This is probably random depending the marble height of that specific channel or neighbouring channels, 
# so I give each channel a random value between these two (uniformly)
CHANNEL_ACCEPT_PROB_MIN = 0.4
CHANNEL_ACCEPT_PROB_MAX = 0.8

# How many times will the crank need to be turned before a dropped marble gets back to the top of the divider
# The conveyor is at least 13 by itself, then you have the ring lifts and the marbles rolling from the drops to the lifts
BEATS_UNTIL_MARBLE_RETURN = 32
# Same as above but for marble recycle by fishstair
BEATS_UNTIL_MARBLE_RECYCLE = 12

# ----- CONVEYOR settings -----
CONVEYOR_NUM_CHANNELS = 8
# Number of beats between releases of marbles onto the divider
CONVEYOR_BEATS_PER_RELEASE = 1
# The probability that a channel of the conveyor will actually accept a marble if one is available
CONVEYOR_CHANNEL_ACCEPT_PROB = 0.95
# Where do the first and last marble lanes enter the divider?
CONVEYOR_DIVIDER_ENTRY_START = 4
CONVEYOR_DIVIDER_ENTRY_END = NUM_CHANNELS - 8
# How many marbles can be waiting for the conveyor?
CONVEYOR_RESERVOIR_CAPACITY = 80
# Initial marbles will end up just getting dumped into the fishstair pool so this is a bit redundant
CONVEYOR_RESERVOIR_INITIAL = 0

# ----- FISHSTAIR settings -----
FISHSTAIR_NUM_CHANNELS = 4
# Number of beats between releases of marbles onto the divider
FISHSTAIR_BEATS_PER_RELEASE = 2
FISHSTAIR_CHANNEL_ACCEPT_PROB = 0.95
# The fishstair goes straight on at the start of the divider
FISHSTAIR_DIVIDER_ENTRY = 0
# How many marbles can be waiting for the conveyor? 
FISHSTAIR_RESERVOIR_CAPACITY = 4*120
# !!!! This seems important: !!!!
FISHSTAIR_RESERVOIR_INITIAL = 4*100

# How many marbles to drop before we give up trying to break the MMX?
LONG_RUN_MARBLE_GOAL = 1_000_000

# Try flipping the divider direction to see if it improves things
# This seems to make things worse if anything as it means that the bass is only fed by 
# the two marbles per beat of the fishstair, and nothing else.
REVERSE_DIVIDER = False


# Compute conveyor belt entry points assuming uniform spread
CONVEYOR_CHANNEL_ENTRY_POINTS = [
    int(CONVEYOR_DIVIDER_ENTRY_START + 
        (CONVEYOR_DIVIDER_ENTRY_END-CONVEYOR_DIVIDER_ENTRY_START)*(i/(CONVEYOR_NUM_CHANNELS-1)))
    for i in range(CONVEYOR_NUM_CHANNELS)
]


@dataclass
class Channel:
    index: int
    marble_accept_p: float
    count: int = MAX_MARBLES_PER_CHANNEL
    max_count: int = MAX_MARBLES_PER_CHANNEL

"""
class MarbleWait:
    def __init__(self, length, initial, capacity):
        self.reservoir_waiting = 0
        self.reservoir_capacity = 0

        self.queue = [0] * length
    
    def simul_step(self):
        self.reservoir_waiting += self.queue[0]
        self.queue = self.queue[1:] + [0]

    def add_marbles(self, n):
        self.queue[-1] += n
    
    def take_channels(self, n, accept_prob) -> list[bool]:
        output = [False] * n

        for c in range(n):
            if self.reservoir_waiting <= 0:
                break
            
            if bernoulli(accept_prob):
                self.reservoir_waiting -= 1
                output[c] = True
        
        return output

    @property
    def overflowed(self) -> bool:
        return self.reservoir_waiting > self.reservoir_capacity
"""

class MMX:
    def __init__(self, song):
        self.channels: list[Channel] = [Channel(i, randf(CHANNEL_ACCEPT_PROB_MIN, CHANNEL_ACCEPT_PROB_MAX)) for i in range(NUM_CHANNELS)]
        self.fishstair_waiting = FISHSTAIR_RESERVOIR_INITIAL
        self.conveyor_waiting = CONVEYOR_RESERVOIR_INITIAL

        self.return_queue = [0] * BEATS_UNTIL_MARBLE_RETURN
        self.recycle_queue = [0] * BEATS_UNTIL_MARBLE_RECYCLE

        self.song = song
        self.song_i = 0

    def divide_marble(self, start: int):
        def channel_step(c):
            if self.channels[c].count >= self.channels[c].max_count:
                return False
            if bernoulli(self.channels[c].marble_accept_p):
                self.channels[c].count += 1
                return True

        if not REVERSE_DIVIDER:
            for c in range(start, NUM_CHANNELS):
                if channel_step(c): return
        else:
            for c in range(NUM_CHANNELS - start - 1, -1, -1):
                if channel_step(c): return
        self.recycle_queue[-1] += 1

    def simul_step(self):
        # Return and recycle queues moves forward
        self.conveyor_waiting += self.return_queue[0]
        self.return_queue = self.return_queue[1:] + [0]

        self.fishstair_waiting += self.recycle_queue[0]
        self.recycle_queue = self.recycle_queue[1:] + [0]

        # Redistribute Marbles
        if (self.song_i % CONVEYOR_BEATS_PER_RELEASE) == 0:
            for conveyor_c in range(CONVEYOR_NUM_CHANNELS):
                if self.conveyor_waiting <= 0:
                    continue
                
                if bernoulli(CONVEYOR_CHANNEL_ACCEPT_PROB):
                    self.conveyor_waiting -= 1
                    self.divide_marble(CONVEYOR_CHANNEL_ENTRY_POINTS[conveyor_c])

        if (self.song_i % FISHSTAIR_BEATS_PER_RELEASE) == 0:
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

        for c in self.song.notes_on_beat(self.song_i):
            if self.channels[c].count <= 0:
                print("Fired an empty channel")
                played_empty = True
                continue
            self.channels[c].count -= 1
            self.return_queue[-1] += 1
            num_played += 1                
        
        self.song_i += 1

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
    song = MMXSong.make_random()

    with open("song.txt", "w") as f:
        f.write(repr(song))

    mmx = MMX(song)
    num_played = 0
    ran_dry = False

    conveyor_overflow_already = False
    fishstair_overflow_already = False

    last_report = 0

    if DO_PLOTTING:
        marbles_dropped_list = []
        min_marbles_list = []
        conveyor_waiting_list = []
        fishstair_waiting_list = []

        fig, (min_marbles_ax, conveyor_ax, fishstair_ax, marble_ax) = plt.subplots(4, sharex=True)
        min_marbles_ax.set_title('Min marbles in a channel')
        conveyor_ax.set_title('Conveyor waiting')
        fishstair_ax.set_title('Fishstair waiting')
        marble_ax.set_title('Marbles Dropped')

    print()

    while num_played <= LONG_RUN_MARBLE_GOAL:
        num_played_incr, played_empty, fishstair_overflowed, conveyor_overflowed = mmx.simul_step()
        if played_empty:
            print("Ran dry after {0} marbles dropped, {1} crank turns, or {2:.2f} plays of the song".format(
                num_played, mmx.song_i, mmx.song_i / song.beat_count))
            ran_dry = True
            break
        if fishstair_overflowed and not fishstair_overflow_already:
            fishstair_overflow_already = True
            print("Fishstair overflowed after {0} marbles dropped, {1} crank turns, or {2:.2f} plays of the song".format(
                num_played, mmx.song_i, mmx.song_i / song.beat_count))
        if conveyor_overflowed and not conveyor_overflow_already:
            conveyor_overflow_already = True
            print("Conveyor overflowed after {0} marbles dropped, {1} crank turns, or {2:.2f} plays of the song".format(
                num_played, mmx.song_i, mmx.song_i / song.beat_count))
        num_played += num_played_incr

        if DO_PLOTTING:
            marbles_dropped_list.append(num_played)
            min_marbles_list.append(min(c.count for c in mmx.channels))
            fishstair_waiting_list.append(mmx.fishstair_waiting)
            conveyor_waiting_list.append(mmx.conveyor_waiting)

        if num_played > (last_report + (LONG_RUN_MARBLE_GOAL/10)):
            last_report += LONG_RUN_MARBLE_GOAL/10
            print("Played {0} marbles".format(num_played))

    if not ran_dry:
        print("Never ran dry")
    print()
    print(repr(mmx))
    
    if DO_PLOTTING:
        min_marbles_ax.plot(range(len(marbles_dropped_list)), min_marbles_list)
        conveyor_ax.plot(range(len(marbles_dropped_list)), conveyor_waiting_list)
        fishstair_ax.plot(range(len(marbles_dropped_list)), fishstair_waiting_list)
        marble_ax.plot(range(len(marbles_dropped_list)), marbles_dropped_list)
        plt.show()
