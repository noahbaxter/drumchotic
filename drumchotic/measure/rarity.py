"""How rare a chart's note patterns are across the library. A run of notes that many artists' charts
play is one players already have under their fingers; a run nobody else plays has to be learned.
Rarity is library-wide, so it is scored in a second pass (drumchotic/tools/build_rarity.py)."""
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..chart.model import Pad
from ..tuning import RARITY_GRID, RARITY_RUN
from .playable import playable
from .timing import worst_window

WINDOWS_S = (4, 16)
_P = np.uint64(1000003)
_START = np.uint64(7919)


def artist(meta):
    return str(meta.get('artist', '')).strip().lower()


def runs(chart):
    """(onset times ms, one hash per run of RARITY_RUN onsets, starting at each onset).

    An onset is everything played on one tick (a chord is one onset): which of kick, drum and
    cymbal it has, and the gap to the next onset on a RARITY_GRID-per-beat grid. The run's
    hash also takes where its first onset sits in the beat, so the same notes shifted off the
    beat are a different pattern."""
    by = {}
    for h in playable(chart):
        by.setdefault(h.tick, [0, h.time_ms])[0] |= 1 if h.pad == Pad.KICK else (4 if h.cymbal else 2)
    ticks = np.array(sorted(by), dtype=np.int64)
    t = np.array([by[k][1] for k in ticks], dtype=float)
    n = len(ticks) - RARITY_RUN      # runs with a gap after every onset
    if n < 1:
        return t, np.zeros(0, np.uint64)
    res = chart.resolution
    code = np.array([by[k][0] for k in ticks], dtype=np.uint64)
    gaps = np.minimum(np.rint(np.diff(ticks) * RARITY_GRID / res), 4 * RARITY_GRID).astype(np.uint64)
    tok = (code[:-1] << np.uint64(8)) | gaps
    beat_pos = np.rint((ticks[:n] % res) * RARITY_GRID / res).astype(np.uint64) % np.uint64(RARITY_GRID)
    h = beat_pos * _START
    for j in range(RARITY_RUN):
        h = h * _P + tok[j:n + j] + np.uint64(1)
    return t, h


@dataclass
class Table:
    """How many artists play each run, over the library."""
    hashes: np.ndarray      # sorted, unique
    counts: np.ndarray      # artists per hash
    artists: int

    @classmethod
    def build(cls, by_artist):
        """by_artist: artist -> list of run-hash arrays, one per chart."""
        per = [np.unique(np.concatenate(v)) for v in by_artist.values()]
        hashes, counts = np.unique(np.concatenate(per), return_counts=True)
        return cls(hashes, counts, len(by_artist))

    def save(self, path):
        np.savez(path, hashes=self.hashes, counts=self.counts, artists=self.artists)

    @classmethod
    def load(cls, path):
        with np.load(Path(path)) as z:
            return cls(z['hashes'], z['counts'], int(z['artists']))

    def rarity(self, h, in_table):
        """log(artists / (other artists playing the run + 1)) per run. in_table: the chart's own artist
        is in the table and always has its own runs, so take it out."""
        i = np.minimum(np.searchsorted(self.hashes, h), len(self.hashes) - 1)
        df = np.where(self.hashes[i] == h, self.counts[i], 0) - (1 if in_table else 0)
        return np.log(self.artists / (np.maximum(df, 0) + 1.0))


EMPTY = {'rarity_mean': 0.0, **{f'rarity_w{w}': 0.0 for w in WINDOWS_S}}


def features(t, h, table, in_table):
    """Mean rarity per run, and the densest 4s and 16s of it."""
    if not len(h):
        return dict(EMPTY)
    rar = table.rarity(h, in_table)
    tt = t[:len(h)]
    return {'rarity_mean': float(rar.mean()), **{f'rarity_w{w}': worst_window(tt, rar, w) for w in WINDOWS_S}}
