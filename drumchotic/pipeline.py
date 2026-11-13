"""Fit everything from the feature caches once; the tools and web pages read the result."""
import collections
import functools
import hashlib
import json
import pickle
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from .chart import song
from .fit import players
from .fit.axes import AxisModel
from .fit.metrics import tier_accuracy
from .measure import rarity
from .sources import dmt, leaderboard, rockband, tournaments
from .tuning import AXES, MIN_NOTES, MIN_SCORES

DATA = Path('data')
FOLDS = 5
BOOTSTRAPS = 200


def load_features(*names):
    """md5 -> {'folder', 'title', 'features'}, rarity features (build_rarity) folded in."""
    out = {}
    for n in names:
        p = DATA / 'cache' / n
        if p.exists():
            out.update(json.loads(p.read_text()))
    rare = json.loads((DATA / 'cache/rarity.json').read_text())
    for m, e in out.items():
        e['features'].update(rare[m])
    return out


@functools.cache
def rarity_table():
    """The library's run table, for scoring rarity on charts outside the library."""
    return rarity.Table.load(DATA / 'cache/rarity_table.npz')


@dataclass
class Results:
    library: dict        # md5 -> {'folder', 'features'} for scored/tiered charts
    anchors: dict        # md5 -> {'folder', 'features'} for suggested superhuman charts
    features: dict       # md5 -> features, library and anchors
    songs: dict          # md5 -> leaderboard.Song
    fit: players.Fit     # leaderboard difficulty and player skill
    labels: list         # [(dmt.Label, md5)]
    rock_band: list      # [rockband.Label]: official Rock Band drum tiers
    pool: list           # md5s used as training targets
    held_out: dict       # md5 -> prediction from a model that never saw that chart (pool only)
    tier_pred: dict      # md5 -> prediction from a model trained without any DMT chart
    model: AxisModel     # trained on the whole pool
    pred: dict           # md5 -> difficulty, library and anchors
    axes: dict           # axis -> {md5: axis score}

    def name(self, md5):
        """song.ini title first: the DMBot export has some names with mangled characters."""
        entry = self.library.get(md5) or self.anchors.get(md5) or {}
        s = self.songs.get(md5)
        return entry.get('title') or (f'{s.artist} - {s.name}' if s else md5)

    def pool_scores(self):
        """Leaderboard difficulty and held-out prediction for every pool chart, as two arrays."""
        return (np.array([self.fit.difficulty[m] for m in self.pool]),
                np.array([self.held_out[m] for m in self.pool]))

    def shares(self, ms):
        """Each axis's slice of difficulty above the intercept, {axis: array}. With the power mean
        S = (sum a^p)^(1/p), a^p / S^(p-1) sums to S exactly, so the slices add up to pred - intercept,
        less the length discount on long charts."""
        p = self.model.power
        a = np.array([[self.axes[x][m] for m in ms] for x in AXES])
        S = (a ** p).sum(0) ** (1 / p)
        return dict(zip(AXES, a ** p / np.where(S > 0, S, 1) ** (p - 1)))

    def noise(self):
        """Bootstrap sd of the held-out Spearman (over charts) and tier accuracy (over tournaments)."""
        rng = np.random.default_rng(0)
        lb, ho = self.pool_scores()
        sp = [spearmanr(lb[i], ho[i])[0] for i in (rng.integers(0, len(lb), len(lb)) for _ in range(BOOTSTRAPS))]
        groups = collections.defaultdict(list)
        for lab, m in self.labels:
            groups[lab.group].append((lab, m))
        names = list(groups)
        tiers = [tier_accuracy([x for i in rng.choice(len(names), len(names)) for x in groups[names[i]]], self.tier_pred)
                 for _ in range(BOOTSTRAPS)]
        return float(np.std(sp)), float(np.std(tiers))


def fold_of(pool):
    """Which held-out fold each pool chart lands in; fixed so every fit sees the same split."""
    return np.random.default_rng(0).integers(0, FOLDS, len(pool))


def held_out_sets(pool, dmt_md5):
    """Training sets: one per held-out fold, then one without any DMT chart."""
    fold = fold_of(pool)
    sets = [[m for m, f in zip(pool, fold) if f != k] for k in range(FOLDS)]
    return sets + [[m for m in pool if m not in dmt_md5]]


def predict_held_out(folds, pool, F):
    """md5 -> prediction from the fold model that never saw that chart."""
    fold = fold_of(pool)
    out = {}
    for k, mdl in enumerate(folds):
        test = [m for m, f in zip(pool, fold) if f == k]
        out.update(zip(test, mdl.predict([F[m] for m in test])))
    return out


def train(job):
    """job: (features, targets, weights, axes); axes None means every axis in tuning.AXES."""
    feats, y, w, axes = job
    return AxisModel(axes=axes).fit(feats, y, w)


def player_fit(songs, note_counts):
    """The leaderboard fit, cached on disk until its inputs, knobs or code change."""
    scored = {m: s for m, s in songs.items() if len(s.scores) >= 3}
    sources = [DATA / 'leaderboards/songs_new_rows.csv', *sorted((DATA / 'results').rglob('*'))]
    key = hashlib.sha1(repr((
        players.PRIOR, players.ROBUST, players.T_WEIGHT, players.MIN_PERCENT,
        Path(players.__file__).read_bytes(),
        [(str(p), p.stat().st_size, p.stat().st_mtime_ns) for p in sources if p.is_file()],
        sorted(note_counts.items()),
    )).encode()).hexdigest()
    path = DATA / 'cache/players.pkl'
    if path.exists():
        cached_key, fit = pickle.loads(path.read_bytes())
        if cached_key == key:
            return fit
    users = {s.username for so in scored.values() for s in so.scores}
    fit = players.fit(scored, note_counts, tournaments.pairs(tournaments.load(DATA / 'results', users)))
    path.write_bytes(pickle.dumps((key, fit)))
    return fit


def run():
    library = load_features('features.json', 'features_dmt.json')
    anchors = load_features('features_anchors.json')
    F = {m: v['features'] for m, v in {**library, **anchors}.items()}
    songs = leaderboard.load(DATA / 'leaderboards/songs_new_rows.csv', min_scores=1)
    fit = player_fit(songs, {m: int(f['notes']) for m, f in F.items()})
    d, nsc = fit.difficulty, fit.n_scores
    labels = [(lab, song.md5(lab.folder)) for lab in dmt.load(DATA / 'dmt')]
    dmt_md5 = {m for _, m in labels}
    pool = [m for m in library if m in d and nsc[m] >= MIN_SCORES and F[m]['notes'] >= MIN_NOTES]

    # 5 held-out folds, one model that never saw a DMT chart, one on everything: independent, so in parallel
    train_sets = held_out_sets(pool, dmt_md5) + [pool]
    jobs = [([F[m] for m in ms], [d[m] for m in ms], [nsc[m] for m in ms], None) for ms in train_sets]
    with ProcessPoolExecutor(len(jobs)) as ex:
        *folds, no_dmt, model = ex.map(train, jobs)
    held_out = predict_held_out(folds, pool, F)
    tier_pred = dict(zip(library, no_dmt.predict([F[m] for m in library])))
    allm = list(F)
    pred = dict(zip(allm, model.predict([F[m] for m in allm])))
    axes = {a: dict(zip(allm, v)) for a, v in model.axis_scores([F[m] for m in allm]).items()}
    return Results(library, anchors, F, songs, fit, labels, rockband.load(library), pool, held_out, tier_pred, model, pred, axes)
