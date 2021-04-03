import math
from utils import *


def song_repr(song: list[list[bool]]):
    return "\n".join(("".join(["*" if note else "-" for note in c_notes]) for c_notes in song))


def blank_song(num_channels: int, num_crank_turns: int) -> list[list[bool]]:
    song: list[list[bool]] = [[False]*num_crank_turns]*num_channels
    song = list(map(list, song))  # Make all the lists truly independent
    return song

def generate_note_counts_per_channel(num_channels: int, marbles_per_song: int, channel_minmax_weight: float):
    c_wts: list[float] = [
        randf(1, channel_minmax_weight) for c in range(num_channels)]
    t_wt: float = sum(c_wts)
    c_counts: list[int] = [math.floor(
        (wt/t_wt)*marbles_per_song) for wt in c_wts]
    
    return c_counts

def make_song_from_counts(num_channels: int, num_crank_turns: int, c_counts: list[int]):
    song = blank_song(num_channels, num_crank_turns)
    for c in range(num_channels):
        for _ in range(c_counts[c]):
            # Find an empty place to put a new note
            i = random.randrange(num_crank_turns)
            while song[c][i]:
                i = random.randrange(num_crank_turns)
            song[c][i] = True
    return song

def make_song(num_channels: int, num_crank_turns: int, marbles_per_song: int, channel_minmax_weight: float):
    c_counts = generate_note_counts_per_channel(num_channels, marbles_per_song, channel_minmax_weight)
    
    return make_song_from_counts(num_channels, num_crank_turns, c_counts)


def convert_to_alternating(song, num_channelpairs: int, num_crank_turns: int):
    song_modified = blank_song(num_channelpairs * 2, num_crank_turns)

    for p in range(num_channelpairs):
        count = 0
        for i in range(num_crank_turns):
            for j in range(2):
                if song[p*2 + j][i]:
                    song_modified[p*2 + (count % 2)][i] = True
                    count += 1

    return song_modified

def make_song_channels_paired(num_channelpairs: int, num_crank_turns: int, marbles_per_song: int, channel_minmax_weight: float):
    # Generate counts for each channel pair
    cp_counts = generate_note_counts_per_channel(num_channelpairs, marbles_per_song, channel_minmax_weight)

    # Split these into the pairs
    c_counts = sum([[math.floor(count/2), math.ceil(count/2)] for count in cp_counts], start=[])

    song = make_song_from_counts(num_channelpairs*2, num_crank_turns, c_counts)
    return convert_to_alternating(song, num_channelpairs, num_crank_turns)


def make_song_channels_paired_sectioned(
    num_channelpairs: int, num_sections: int, num_crank_turns_per_section: int, 
    marbles_per_section: int, channel_minmax_weight: float):
    sections = [make_song_channels_paired(num_channelpairs, num_crank_turns_per_section, marbles_per_section, channel_minmax_weight) for s in range(num_sections)]

    song = [sum([sections[s][c] for s in range(num_sections)], start=[]) for c in range(num_channelpairs*2)]

    return convert_to_alternating(song, num_channelpairs, num_sections * num_crank_turns_per_section)
