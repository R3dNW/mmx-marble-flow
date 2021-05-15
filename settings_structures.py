from typing import NamedTuple

class InstrumentSettings(NamedTuple):
    num_cps: int
    npb: float
    ratio: float 
    name: str = ""

class SongMuteInstruction(NamedTuple):
    mask: int
    length: int
    name: str = ""

class MarbleTransportSettings(NamedTuple):
    num_channels: int
    channel_accept_p: float

    beats_per_release: int

    beats_to_transport: int

    # Assume the entries onto the divider are evenly spaced between these two points
    divider_entry_start: int
    divider_entry_end: int
    
    reservoir_capacity: int
    reservoir_initial: int

