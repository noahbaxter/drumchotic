"""The notes a player actually has to hit, as opposed to every note in the file."""
from ..chart.model import Pad
from ..tuning import KICK_MODE, ROLL_MODE


def playable(chart, kick_mode=KICK_MODE, roll_mode=ROLL_MODE):
    hits = chart.hits
    if kick_mode == '1x':
        hits = [h for h in hits if not (h.pad == Pad.KICK and h.kick2x)]
    return apply_rolls(hits, chart.rolls, roll_mode)


def apply_rolls(hits, rolls, mode=ROLL_MODE):
    """Roll lanes let you hit freely, so their notes aren't all required.
    'half' keeps every other note per pad (the rate needed to not miss)."""
    if mode == 'full' or not rolls:
        return hits
    drop = set()
    for r in rolls:
        by_pad = {}
        for h in hits:
            if r.start_ms <= h.time_ms < r.end_ms:
                by_pad.setdefault(h.pad, []).append(h)
        for seq in by_pad.values():
            drop.update(id(h) for h in (seq if mode == 'skip' else seq[1::2]))
    return [h for h in hits if id(h) not in drop]
