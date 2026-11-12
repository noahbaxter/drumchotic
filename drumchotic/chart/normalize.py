"""Shared last step of both parsers: raw expert lanes -> 4-lane pro Hits."""
import re
from dataclasses import dataclass

from .model import Dynamic, Hit, Pad, TrackType

KICK_LANE = 0
FIVE_LANE_GREEN = 5

# 5-lane -> 4-lane pro, from the chart-format spec's conversion table
FIVE_LANE_TO_PRO = {
    1: (Pad.RED, False),
    2: (Pad.YELLOW, True),
    3: (Pad.BLUE, False),
    4: (Pad.GREEN, True),   # orange
    5: (Pad.GREEN, False),  # green
}

EXPERT_MIX = re.compile(r'mix[ _]3[ _]drums\d([a-z]*)', re.I)
DISCO_FLAG = 'd'


@dataclass
class RawNote:
    tick: int
    lane: int             # 0 kick, 1-5 hand lanes in file order
    cymbal: bool = False  # parser's 4-lane cymbal reading; ignored for 5-lane
    kick2x: bool = False
    dynamic: Dynamic = Dynamic.NORMAL
    flam: bool = False


def track_type(ini, raw):
    if ini.get('five_lane_drums') and not ini.get('pro_drums'):
        return TrackType.FIVE_LANE
    if ini.get('pro_drums'):
        return TrackType.FOUR_LANE
    return TrackType.FIVE_LANE if any(n.lane == FIVE_LANE_GREEN for n in raw) else TrackType.FOUR_LANE


def disco_ranges(mix_events):
    """mix_events: (tick, text). Returns [start, end) tick ranges where expert disco flip is on."""
    ranges, start = [], None
    for tick, text in sorted(mix_events):
        m = EXPERT_MIX.search(text)
        if not m:
            continue
        if start is not None:
            ranges.append((start, tick))
            start = None
        if m.group(1).lower() == DISCO_FLAG:
            start = tick
    if start is not None:
        ranges.append((start, float('inf')))
    return ranges


def in_ranges(tick, ranges):
    return any(a <= tick < b for a, b in ranges)


def _pad(note, ttype):
    if note.lane == KICK_LANE:
        return Pad.KICK, False
    if ttype == TrackType.FIVE_LANE:
        return FIVE_LANE_TO_PRO[note.lane]
    pad = Pad(min(note.lane, Pad.GREEN))
    return pad, note.cymbal and pad != Pad.RED


def _disco_flip(pad, cymbal):
    if pad == Pad.RED:
        return Pad.YELLOW, True
    if pad == Pad.YELLOW and cymbal:
        return Pad.RED, False
    return pad, cymbal


def build_hits(raw, ttype, tempo, disco=()):
    by_tick = {}
    for note in raw:
        by_tick.setdefault(note.tick, []).append(note)

    hits = {}
    for tick, notes in by_tick.items():
        lanes = {n.lane for n in notes}
        for note in notes:
            pad, cymbal = _pad(note, ttype)
            # spec: 5-lane orange + green together -> green cymbal + blue tom
            if ttype == TrackType.FIVE_LANE and note.lane == FIVE_LANE_GREEN and 4 in lanes:
                pad = Pad.BLUE
            if ttype == TrackType.FOUR_LANE and disco and in_ranges(tick, disco):
                pad, cymbal = _disco_flip(pad, cymbal)
            key = (tick, pad, cymbal)
            prev = hits.get(key)
            # a 1x and 2x kick on one tick is a single kick, readable on one pedal
            if prev is None or (prev.kick2x and not note.kick2x):
                hits[key] = Hit(tick, tempo.ms(tick), pad, cymbal, note.kick2x, note.dynamic, note.flam)
    return sorted(hits.values(), key=lambda h: (h.tick, h.pad))
