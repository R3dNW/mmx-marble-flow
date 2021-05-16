from dataclasses import dataclass
import random
import math
from typing import List, Tuple, Dict

from settings import *
from song import MMXSong
from utils import *

if DO_PLOTTING:
    import matplotlib.pyplot as plt


# A single channel of the MMX
@dataclass
class Channel:
    index: int
    marble_accept_p: float
    count: int = MAX_MARBLES_PER_CHANNEL
    max_count: int = MAX_MARBLES_PER_CHANNEL


# 'Circular Queue'-like object representing the marbles on their journey to the end of the Marble Transport
class TransportQueue:
    def __init__(self, length):
        self.__length = length
        self.__head = 0
        self.__data = [0] * self.__length

    def pop(self):
        val = self.__data[self.__head]
        self.__data[self.__head] = 0
        self.__head = (self.__head + 1) % self.__length
        return val

    def add_to_tail(self, count):
        self.__data[(self.__head - 1) % self.__length] += count
    
    def __iter__(self):
        return iter(self.__data[self.__head:] + self.__data[:self.__head])


# Marble return or recycle (i.e. fishstair or conveyor)
class MarbleTransport:
    def __init__(self, t_settings: MarbleTransportSettings):
        self.settings: MarbleTransportSettings = t_settings
        self.reservoir_waiting: int = self.settings.reservoir_initial
        self.queue: TransportQueue = TransportQueue(self.settings.beats_to_transport)

        self.divider_entry_points = [
            int(self.settings.divider_entry_start +
                (self.settings.divider_entry_end-self.settings.divider_entry_start)*(i/(self.settings.num_channels-1)))
            for i in range(self.settings.num_channels)
        ]

    def simul_step(self, song_i):
        self.reservoir_waiting += self.queue.pop()

        if (song_i % self.settings.beats_per_release) == 0:
            for c in range(self.settings.num_channels):
                if self.reservoir_waiting <= 0:
                    break

                if bernoulli(self.settings.channel_accept_p):
                    self.reservoir_waiting -= 1
                    yield self.divider_entry_points[c]

    def add_marbles(self, n):
        self.queue.add_to_tail(n)

    @property
    def overflowed(self) -> bool:
        return self.reservoir_waiting > self.settings.reservoir_capacity

    def __repr__(self):
        return "MarbleTransport [\n\tWaiting: {0}\n\tQueue: [{1}]\n]".format(
            self.reservoir_waiting,
            ", ".join(map(str, self.queue))
        )

# The actual MMX
class MMX:
    def __init__(self, song):
        self.channels: List[Channel] = [Channel(i, randf(
            CHANNEL_ACCEPT_PROB_MIN, CHANNEL_ACCEPT_PROB_MAX)) for i in range(NUM_CHANNELS)]
        
        self.return_transport = MarbleTransport(MARBLE_RETURN_SETTINGS)
        self.recycle_transport = MarbleTransport(MARBLE_RECYCLE_SETTINGS)

        self.song = song
        self.song_i = 0

    def divide_marble(self, start: int):
        loop = None
        if not REVERSE_DIVIDER:
            loop = range(start, NUM_CHANNELS)
        else:
            loop = range(NUM_CHANNELS - start - 1, -1, -1)
        
        for c in loop:
            if self.channels[c].count >= self.channels[c].max_count:
                continue
            if bernoulli(self.channels[c].marble_accept_p):
                self.channels[c].count += 1
                break
        else:
            self.recycle_transport.add_marbles(1)

    def simul_step(self):
        # Return and recycle transports are simul_step()ed and we divide their marbles
        for marble_start in self.return_transport.simul_step(self.song_i):
            self.divide_marble(marble_start)
        for marble_start in self.recycle_transport.simul_step(self.song_i):
            self.divide_marble(marble_start)

        # Play Notes
        num_played = 0
        played_empty = False
        fishstair_overflowed = self.recycle_transport.overflowed
        conveyor_overflowed = self.return_transport.overflowed

        for c in self.song.notes_on_beat(self.song_i):
            if self.channels[c].count <= 0:
                print("Fired an empty channel")
                played_empty = True
                continue
            self.channels[c].count -= 1
            num_played += 1
        
        self.return_transport.add_marbles(num_played)

        self.song_i += 1

        return num_played, played_empty, fishstair_overflowed, conveyor_overflowed

    def __repr__(self):
        return "MMX [\n\tChannels: [{0}], \n\tReturn: {1}, \n\tRecycle: {2}, \n]".format(
            ", ".join(str(channel.count) for channel in self.channels),
            repr(self.return_transport).replace("\n", "\n\t"),
            repr(self.recycle_transport).replace("\n", "\n\t"),
        )


def run_sim():
    song = None
    if SONG_PATH == None:
        song = MMXSong.make_random()
    else:
        song = MMXSong.from_file(SONG_PATH)

    print(song)

    #with open("song.txt", "w") as f:
    #    f.write(repr(song))

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

        fig, (min_marbles_ax, conveyor_ax, fishstair_ax,
              marble_ax) = plt.subplots(4, sharex=True)
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
            conveyor_waiting_list.append(mmx.return_transport.reservoir_waiting)
            fishstair_waiting_list.append(mmx.recycle_transport.reservoir_waiting)

        if num_played > (last_report + (LONG_RUN_MARBLE_GOAL/REPORT_COUNT)):
            last_report += LONG_RUN_MARBLE_GOAL/REPORT_COUNT
            print("Played {0} marbles, {1} crank turns, or {2:.2f} plays of the song".format(
                num_played, mmx.song_i, mmx.song_i / song.beat_count))

    if not ran_dry:
        print("Never ran dry")
    print()
    print(repr(mmx))

    if DO_PLOTTING:
        min_marbles_ax.plot(range(len(marbles_dropped_list)), min_marbles_list)
        conveyor_ax.plot(range(len(marbles_dropped_list)),
                         conveyor_waiting_list)
        fishstair_ax.plot(range(len(marbles_dropped_list)),
                          fishstair_waiting_list)
        marble_ax.plot(range(len(marbles_dropped_list)), marbles_dropped_list)
        plt.show()

if __name__ == "__main__":
    run_sim()
