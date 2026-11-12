"""Model scores read as an estimated DMT tier and a suggested diff_drums, and the axes that make
a chart hard compared with charts of the same level. The rate tool and the explorer read these."""
import collections
from pathlib import Path

import numpy as np

from . import pipeline
from .chart import ini
from .tuning import AXES

PEERS = 300            # charts either side in difficulty order that count as "the same level"
STANDS_OUT = 85        # peer percentile an axis needs to be listed as a reason
MIN_PER_LEVEL = 20     # labels with fewer library charts don't anchor a scale
# Charter ratings below this don't follow difficulty (0 mostly means unrated, 1 and 2 overlap),
# so the charter scale is built from this rating up and extends its slope downward.
CHARTER_FROM = 2
REASONS_SHOWN = 3      # stand-out axes listed per chart


class Scale:
    """Model score -> a labelled scale, by interpolating between each label's median score.
    Past either end it keeps that end's slope, so 8.6 reads as 'well past a typical 8'."""

    def __init__(self, scores, labels):
        s, lab = np.asarray(scores), np.asarray(labels)
        levels = sorted(v for v in set(labels) if (lab == v).sum() >= MIN_PER_LEVEL)
        self.levels = np.array(levels, float)
        self.medians = np.maximum.accumulate([np.median(s[lab == v]) for v in levels])

    def __call__(self, x):
        lv, md = self.levels, self.medians
        if x > md[-1]:
            v = lv[-1] + (x - md[-1]) / max(md[-1] - md[-2], 1e-9) * (lv[-1] - lv[-2])
        elif x < md[0]:
            v = lv[0] - (md[0] - x) / max(md[1] - md[0], 1e-9) * (lv[1] - lv[0])
        else:
            v = np.interp(x, md, lv)
        return max(0.0, float(v))


class Rater:
    def __init__(self):
        r = self.r = pipeline.run()
        self.lib = list(r.library)
        self.pred = np.array([r.pred[m] for m in self.lib])
        self.order = np.argsort(self.pred)
        self.sorted_pred = self.pred[self.order]
        self.axes = list(AXES)
        self.lib_axes = np.array([[r.axes[a][m] for m in self.lib] for a in self.axes])
        self.lib_sorted = np.sort(self.lib_axes, axis=1)
        rated = [(r.pred[m], d) for m in self.lib
                 if CHARTER_FROM <= (d := charter_rating(r.library[m]['folder'])) <= 6]
        self.charter = Scale(*zip(*rated))
        self.level = Scale(*zip(*[(r.tier_pred[m], lab.tier) for lab, m in r.labels if m in r.tier_pred]))
        self.placed = collections.defaultdict(set)    # md5 -> tiers tournaments placed it in
        for lab, m in r.labels:
            self.placed[m].add(lab.tier)

    def rate(self, feats):
        axis = {a: float(v[0]) for a, v in self.r.model.axis_scores([feats]).items()}
        score = float(self.r.model.predict([feats])[0])
        pos = int(np.searchsorted(self.sorted_pred, score))
        peers = self.order[max(0, pos - PEERS):pos + PEERS]
        rows = []
        for i, a in enumerate(self.axes):
            lib_pct = np.searchsorted(self.lib_sorted[i], axis[a], side='right') / len(self.lib) * 100
            peer_pct = (self.lib_axes[i, peers] < axis[a]).mean() * 100
            rows.append((a, lib_pct, peer_pct))
        return {
            'score': score,
            'level': self.level(score),
            'charter': self.charter(score),
            'axes': rows,
        }


def charter_rating(folder):
    meta = ini.read(Path(folder) / 'song.ini')
    return meta.get('diff_drums_real', meta.get('diff_drums', -1))


def library_title(r, m):
    meta = ini.read(Path(r.library[m]['folder']) / 'song.ini')
    return str(meta.get('artist', '')).strip(), str(meta.get('name', '')).strip() or r.name(m)


def reasons(res):
    return sorted((x for x in res['axes'] if x[2] >= STANDS_OUT), key=lambda x: -x[2])
