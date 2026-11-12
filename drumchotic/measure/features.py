"""Per-chart difficulty features along the axes drummers talk about.

Most axes are a per-event strain summed over sliding windows (tuning.WINDOWS_S);
the chart's value is the worst window, which separates short bursts from
sustained sections. Density and endurance work on fixed-length chunks of the
chart's playing time instead, so they describe the whole chart, not its peak.
"""
import collections
from dataclasses import dataclass

import numpy as np

from . import sticking
from ..chart.model import Pad
from ..chart.tempo import TempoMap
from ..tuning import (DENSITY_BEATS, DENSITY_QUANTILES, ENDURANCE_NPS, NOVEL_HISTORY, REPEAT_WEIGHT,
                      SPEED_WINDOW_S, SUSTAINED_WINDOW_S)
from .playable import playable
from .timing import worst_window


@dataclass
class Onsets:
    """Hits grouped by tick: one entry per moment something is struck."""
    ticks: list
    t: np.ndarray            # ms
    has_kick: np.ndarray
    has_hand: np.ndarray
    surfaces: list           # sorted hand surfaces per onset
    dynamics: np.ndarray     # accented or ghosted hand notes per onset
    novel: np.ndarray        # 1 where the local pattern wasn't seen recently
    weight: np.ndarray       # how much the onset counts toward density/movement strain

    @classmethod
    def of(cls, hits):
        by_tick = {}
        for h in hits:
            by_tick.setdefault(h.tick, []).append(h)
        ticks = sorted(by_tick)
        hands = [[h for h in by_tick[k] if h.pad != Pad.KICK] for k in ticks]
        surfaces = [sorted({sticking.surface(h) for h in hs}) for hs in hands]
        t = np.array([by_tick[k][0].time_ms for k in ticks])
        has_kick = np.array([len(hs) < len(by_tick[k]) for k, hs in zip(ticks, hands)])
        novel = _novelty(t, surfaces, has_kick)
        return cls(
            ticks=ticks,
            t=t,
            has_kick=has_kick,
            has_hand=np.array([bool(s) for s in surfaces]),
            surfaces=surfaces,
            dynamics=np.array([sum(h.dynamic != 0 for h in hs) for hs in hands], dtype=float),
            novel=novel,
            weight=np.where(novel > 0, 1.0, REPEAT_WEIGHT),
        )


def _novelty(t, surfaces, has_kick):
    """1 for onsets whose 4-onset pattern (pads + gaps) wasn't seen in the last NOVEL_HISTORY onsets."""
    tokens = [(tuple(s), bool(k), int(g)) for s, k, g in zip(surfaces, has_kick, gap_tokens(t))]
    return _new_grams(tokens)


def _new_grams(tokens, size=4):
    """1 where the size tokens ending here weren't seen in the last NOVEL_HISTORY tokens."""
    novel = np.zeros(len(tokens))
    seen = {}
    for i in range(size - 1, len(tokens)):
        gram = tuple(tokens[i - size + 1:i + 1])
        last = seen.get(gram)
        if last is None or i - last > NOVEL_HISTORY:
            novel[i] = 1.0
        seen[gram] = i
    return novel


def gap_tokens(t):
    """Gaps between events in 25 ms steps, 0 for the first: rhythm as something to match on."""
    return np.r_[0, np.rint(np.diff(t) / 25.0).astype(int)] if len(t) else np.array([], int)


def compute(chart):
    hits = playable(chart)
    if not hits:
        return None
    o = Onsets.of(hits)
    f = {}
    f.update(speed(hits))
    f.update(density_and_endurance(hits, chart, o))
    f.update({
        'length_s': max((o.t[-1] - o.t[0]) / 1000.0, 1.0),
        'notes': len(chart.hits),     # every note counts toward percent, roll lanes or not
        'rolls': len(chart.rolls),
    })
    return f


def note_times(hits):
    return np.sort(np.array([h.time_ms for h in hits]))


def speed(hits):
    """Max notes per second: the most notes in any SPEED_WINDOW_S, every note counted."""
    t = note_times(hits)
    return {'max_nps': worst_window(t, np.ones(len(t)), SPEED_WINDOW_S)}


def repeat_weights(hits, o):
    """Each hit's onset weight: grooves you lock into count less than new material."""
    weight_at = dict(zip(o.ticks, o.weight))
    return [weight_at[h.tick] for h in hits]


def chunks(hits, chart, weights=None):
    """Notes/s, start ms and end ms of every DENSITY_BEATS chunk that has notes in it. A fixed tick
    span, so time signatures don't bias it. weights: how much each hit counts (default 1)."""
    span = DENSITY_BEATS * chart.resolution
    tempo = TempoMap([(t, 60_000_000 / bpm) for t, bpm in chart.tempos], chart.resolution)
    counts = collections.defaultdict(float)
    for h, w in zip(hits, np.ones(len(hits)) if weights is None else weights):
        counts[h.tick // span] += w
    ks = sorted(counts)
    start = np.array([tempo.ms(k * span) for k in ks])
    end = np.array([tempo.ms((k + 1) * span) for k in ks])
    return np.array([counts[k] for k in ks]) / ((end - start) / 1000.0), start, end


def weighted_quantile(values, weights, q):
    order = np.argsort(values)
    cum = np.cumsum(weights[order])
    return float(values[order][np.searchsorted(cum, q * cum[-1])])


def density_and_endurance(hits, chart, o):
    """Density: notes/s across the playing time (silence skipped, repeats discounted) at
    DENSITY_QUANTILES of time, plus the densest SUSTAINED_WINDOW_S. Endurance: share of playing
    time, and longest unbroken stretch, at or above each ENDURANCE_NPS; neither grows with length."""
    nps, start, end = chunks(hits, chart, repeat_weights(hits, o))
    f = {f'density_p{int(q * 100)}': weighted_quantile(nps, end - start, q) for q in DENSITY_QUANTILES}
    f[f'density_w{SUSTAINED_WINDOW_S}'] = worst_window(o.t, o.weight, SUSTAINED_WINDOW_S)
    dur = (end - start) / 1000.0
    joined = np.r_[False, np.isclose(start[1:], end[:-1])]   # chunk follows the previous with no gap
    for n in ENDURANCE_NPS:
        hot = nps >= n
        f[f'endurance_share_n{n}'] = float(dur[hot].sum() / dur.sum())
        f[f'endurance_longest_n{n}'] = longest_stretch(dur, hot, joined)
    return f


def longest_stretch(dur, hot, joined):
    """Seconds in the longest run of back-to-back hot chunks."""
    best = run = 0.0
    for d, h, j in zip(dur, hot, joined):
        run = (run if j else 0.0) + d if h else 0.0
        best = max(best, run)
    return float(best)
