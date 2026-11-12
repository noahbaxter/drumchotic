from dataclasses import dataclass, field
from enum import Enum, IntEnum


class Pad(IntEnum):
    KICK = 0
    RED = 1
    YELLOW = 2
    BLUE = 3
    GREEN = 4


class Dynamic(IntEnum):
    NORMAL = 0
    ACCENT = 1
    GHOST = 2


class TrackType(Enum):
    FOUR_LANE = '4-lane'
    FIVE_LANE = '5-lane'


@dataclass(frozen=True)
class Hit:
    tick: int
    time_ms: float
    pad: Pad
    cymbal: bool = False
    kick2x: bool = False
    dynamic: Dynamic = Dynamic.NORMAL
    flam: bool = False


@dataclass(frozen=True)
class Span:
    start_ms: float
    end_ms: float
    kind: str


@dataclass
class DrumChart:
    """Expert drums, normalized to 4-lane pro pads (5-lane is converted per the spec table)."""
    source: str
    track_type: TrackType
    # True when the chart carries real cymbal/tom data (markers or pro_drums in song.ini)
    pro_marked: bool
    resolution: int
    hits: list[Hit]
    rolls: list[Span] = field(default_factory=list)
    tempos: list[tuple[int, float]] = field(default_factory=list)      # (tick, bpm)
    time_sigs: list[tuple[int, int, int]] = field(default_factory=list)  # (tick, num, den)

    @property
    def hands(self):
        return [h for h in self.hits if h.pad != Pad.KICK]

    @property
    def kicks(self):
        return [h for h in self.hits if h.pad == Pad.KICK]
