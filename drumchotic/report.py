"""Fit everything from the caches and print how it stacks up. Rerun after tuning.

python -m drumchotic.report [--outliers N]
"""
import sys

import numpy as np
from scipy.stats import spearmanr

from . import pipeline
from .fit.metrics import community_accuracy, tier_accuracy
from .sources import community
from .tuning import AXES


def main(argv):
    show(pipeline.run(), int(argv[argv.index('--outliers') + 1]) if '--outliers' in argv else 15)


def show(r, n_out=15):
    d, nsc, F, pred = r.fit.difficulty, r.fit.n_scores, r.features, r.pred
    lib_pred = np.array([pred[m] for m in r.library])

    def top_axes(m, k=3):
        return ', '.join(f'{a} {r.axes[a][m]:.2f}' for a in sorted(AXES, key=lambda a: -r.axes[a][m])[:k])

    print(f'DMT tiers in the right order (DMT held out): {tier_accuracy(r.labels, r.tier_pred):.3f}')
    print(f'leaderboard difficulty vs held-out prediction: Spearman '
          f'{spearmanr(*r.pool_scores())[0]:.3f} over {len(r.pool)} charts')
    print(f'leaderboard fit only, DMT tiers: {tier_accuracy(r.labels, d):.3f}')
    # held out where the chart is in the leaderboard pool, so claims about scored charts aren't graded on training data
    pairs, missing = community.pairs(community.load(), {m: r.name(m) for m in r.library})
    acc, wrong = community_accuracy(pairs, {m: r.held_out.get(m, pred[m]) for m in r.library})
    print(f'community claims in the right order: {acc:.3f} over {len(pairs)} pairs')
    for c, h, e in wrong:
        print(f'  wrong: {r.name(h)} should beat {r.name(e)}  ({c.source})')
    for t in missing:
        print(f'  no library chart for: {t}')
    print()

    print('Hardest 20:')
    for m in sorted(r.library, key=lambda m: -pred[m])[:20]:
        print(f'  {pred[m]:5.2f}  {r.name(m):50}  {top_axes(m)}')
    if r.anchors:
        print('\nAnchors (suggested superhuman):')
        for m in sorted(r.anchors, key=lambda m: -pred[m]):
            print(f'  {pred[m]:5.2f}  #{int((lib_pred > pred[m]).sum()) + 1:<5} {r.name(m):50}  {top_axes(m)}')

    # outliers: where the chart model and the players disagree most
    res = {m: r.held_out[m] - d[m] for m in r.pool}
    print(f'\nOutliers (held-out prediction minus leaderboard difficulty, sd {np.std(list(res.values())):.2f}):')
    fmt = lambda m: (f'  {res[m]:+5.2f}  pred {r.held_out[m]:5.2f} lb {d[m]:5.2f}  n={nsc[m]:<3} '
                     f'{F[m]["length_s"]:4.0f}s rolls {F[m]["rolls"]:<3.0f} {r.name(m)}')
    print(' we rate it harder than players find it:')
    for m in sorted(r.pool, key=lambda m: -res[m])[:n_out]:
        print(fmt(m))
    print(' players find it harder than we rate it:')
    for m in sorted(r.pool, key=lambda m: res[m])[:n_out]:
        print(fmt(m))

    print('\nFamiliar charts across the scale (most-scored charts in each tenth of the difficulty range):')
    for lo, hi, ms in popular_by_band(r):
        print(f'  {lo:5.2f} to {hi:5.2f}: ' + '; '.join(f'{r.name(m)} ({len(r.songs[m].scores)})' for m in ms))

    print('\nWhere the misses concentrate (residual sd by bucket):')
    for label, test in buckets(r).items():
        x = np.array([res[m] for m in r.pool if test(m)])
        print(f'  {label:26} n={len(x):5}  sd {x.std():.2f}  mean {x.mean():+.2f}')


def popular_by_band(r, bands=10, per_band=4):
    """Equal-width difficulty bands over the scored library, most-scored charts in each."""
    scored = [m for m in r.library if m in r.songs and r.songs[m].scores]
    vals = np.array([r.pred[m] for m in scored])
    edges = np.linspace(np.percentile(vals, 0.5), np.percentile(vals, 99.5), bands + 1)
    out = []
    for lo, hi in zip(edges, edges[1:]):
        ms = [m for m in scored if lo <= r.pred[m] < hi]
        out.append((lo, hi, sorted(ms, key=lambda m: -len(r.songs[m].scores))[:per_band]))
    return out


def buckets(r):
    d, nsc, F = r.fit.difficulty, r.fit.n_scores, r.features
    lat = np.array([d[m] for m in r.pool])
    lo, hi = np.quantile(lat, [1 / 3, 2 / 3])
    return {
        'scores 5-9': lambda m: nsc[m] < 10, 'scores 10-24': lambda m: 10 <= nsc[m] < 25,
        'scores 25+': lambda m: nsc[m] >= 25,
        'length < 90s': lambda m: F[m]['length_s'] < 90, 'length 90-300s': lambda m: 90 <= F[m]['length_s'] < 300,
        'length 300s+': lambda m: F[m]['length_s'] >= 300,
        'has roll lanes': lambda m: F[m]['rolls'] > 0, 'no roll lanes': lambda m: F[m]['rolls'] == 0,
        'leaderboard easiest third': lambda m: d[m] < lo,
        'leaderboard hardest third': lambda m: d[m] > hi,
    }


if __name__ == '__main__':
    main(sys.argv[1:])
