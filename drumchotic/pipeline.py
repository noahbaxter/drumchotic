"""Fit everything from the feature caches once; rate, report, audit, plots and page read the result."""
import hashlib
import json
import pickle
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .chart import song
from .fit import players
from .fit.axes import AxisModel
from .sources import dmt, leaderboard, tournaments
from .tuning import MIN_NOTES, MIN_SCORES

DATA = Path('data')
FOLDS = 5


def load_features(*names):
    out = {}
    for n in names:
        p = DATA / 'cache' / n
        if p.exists():
            out.update(json.loads(p.read_text()))
    return out


@dataclass
class Results:
    library: dict        # md5 -> {'folder', 'features'} for scored/tiered charts
    anchors: dict        # md5 -> {'folder', 'features'} for suggested superhuman charts
    features: dict       # md5 -> features, library and anchors
    songs: dict          # md5 -> leaderboard.Song
    fit: players.Fit     # leaderboard difficulty and player skill
    labels: list         # [(dmt.Label, md5)]
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
    return Results(library, anchors, F, songs, fit, labels, pool, held_out, tier_pred, model, pred, axes)
