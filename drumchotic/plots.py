"""Every plot worth looking at after a tuning pass, dark mode, into data/plots/<timestamp>/.
A run whose plots match the latest folder byte for byte just relabels that folder.

python -m drumchotic.plots [name ...]      no names: every plot
"""
import collections
import datetime
import re
import shutil
import sys
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from scipy.stats import spearmanr

from . import pipeline, report
from .fit.metrics import tier_accuracy
from .tuning import AXES

SURFACE, INK, INK_2, GRID = '#1a1a19', '#f0efec', '#c3c2b7', '#2c2c2a'
OURS, OTHER = '#3987e5', '#d95926'          # validated dark categorical slots 1 and 2
RAMP = LinearSegmentedColormap.from_list('dark_blue', [SURFACE, '#1c5cab', '#3987e5', '#86b6ef', '#cde2fb'])
# easy to hard: purple, blue, green, yellow, orange, red
TIER_CMAP = LinearSegmentedColormap.from_list(
    'difficulty', ['#9085e9', '#3987e5', '#1baf7a', '#eda100', '#eb6834', '#e34948'])


def tier_color(tier, top=8):
    return TIER_CMAP((tier - 1) / max(top - 1, 1))


plt.rcParams.update({
    'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
    'text.color': INK, 'axes.labelcolor': INK_2, 'axes.edgecolor': GRID, 'axes.titlecolor': INK,
    'xtick.color': INK_2, 'ytick.color': INK_2, 'grid.color': GRID, 'grid.linewidth': 0.8,
    'axes.spines.top': False, 'axes.spines.right': False, 'axes.grid': False, 'axes.axisbelow': True,
    'font.size': 11, 'axes.titlesize': 13, 'axes.titlelocation': 'left', 'axes.titlepad': 12,
    'legend.frameon': False,
})


def active_axes(r):
    """Axes the fit actually uses; the rest are flat zero and only add noise to a plot."""
    return [a for a in AXES if max(r.axes[a].values(), default=0) > 0.05]


def dots(ax, xs, groups, colors):
    """Every chart as a dot (spread sideways a little so they don't stack), white dash at the median."""
    rng = np.random.default_rng(0)
    for x, v, c in zip(xs, groups, colors):
        ax.scatter(x + rng.uniform(-0.25, 0.25, len(v)), v, s=14, color=c, alpha=0.8, linewidths=0)
        ax.plot([x - 0.3, x + 0.3], [np.median(v)] * 2, color=INK, lw=2)


def density(ax, x, y, color):
    """A dense scatter as shading: dim = few charts, bright = many."""
    cmap = LinearSegmentedColormap.from_list('d', [SURFACE, color, INK])
    ax.hexbin(x, y, gridsize=55, bins='log', mincnt=1, cmap=cmap, linewidths=0)


def tier_panel(ax, tiers, scores, title):
    t, y = np.asarray(tiers), np.asarray(scores)
    levels = sorted(set(t))
    dots(ax, levels, [y[t == x] for x in levels], [tier_color(x, max(levels)) for x in levels])
    ax.set(title=title, xlabel='DMT tier', xticks=levels)
    ax.grid(axis='y')


def plot_tiers(r):
    fig, axs = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
    for ax, score, color, label in ((axs[0], r.tier_pred, OURS, 'Chart model'),
                                    (axs[1], r.fit.difficulty, OTHER, 'Leaderboard')):
        rows = [(lab.tier, score[m]) for lab, m in r.labels if m in score]
        tier_panel(ax, *zip(*rows), f'{label}  ·  {tier_accuracy(r.labels, score):.1%} in order')
    axs[0].set_ylabel('difficulty')
    return fig


def plot_tournaments(r):
    """Each tournament a column, one coloured dot per tier at that tier's median difficulty."""
    groups = collections.defaultdict(lambda: collections.defaultdict(list))
    for lab, m in r.labels:
        if m in r.tier_pred:
            groups[lab.group][lab.tier].append(r.tier_pred[m])
    year = lambda g: int(next(iter(re.findall(r'20\d\d', g)), 0))
    names = sorted(groups, key=lambda g: (year(g), g))
    top_tier = max(t for g in groups.values() for t in g)
    fig, ax = plt.subplots(figsize=(13, 5.5))
    for x, g in enumerate(names):
        meds = sorted((t, np.median(v)) for t, v in groups[g].items())
        ax.plot([x] * len(meds), [y for _, y in meds], color=GRID, lw=2, zorder=1)
        for t, y in meds:
            ax.scatter([x], [y], s=110, color=tier_color(t, top_tier), edgecolors=SURFACE, linewidths=1.5, zorder=2)
    for t in range(1, top_tier + 1):
        ax.scatter([], [], s=70, color=tier_color(t, top_tier), label=f'tier {t}')
    ax.legend(loc='upper left', bbox_to_anchor=(1.0, 1.0), labelcolor=INK_2)
    ax.set_xticks(range(len(names)), [g.replace(' Setlist', '').replace(' Drum Tournament', '') for g in names],
                  rotation=25, ha='right')
    ax.set_xlim(-0.6, len(names) - 0.4)
    ax.set(ylabel='difficulty', title='Tier medians per tournament')
    ax.grid(axis='y')
    return fig


def plot_model_vs_leaderboard(r):
    lat, hp = r.pool_scores()
    fig, ax = plt.subplots(figsize=(7, 6.5))
    density(ax, lat, hp, OURS)
    lo, hi = min(lat.min(), hp.min()), max(lat.max(), hp.max())
    ax.plot([lo, hi], [lo, hi], color=INK_2, lw=1, ls='--')
    ax.set(title=f'Chart model vs leaderboard  ·  Spearman {spearmanr(lat, hp)[0]:.3f}',
           xlabel='leaderboard difficulty', ylabel='chart model (never saw the chart)')
    return fig


def plot_residuals(r):
    res = {m: r.held_out[m] - r.fit.difficulty[m] for m in r.pool}
    rows = [(label, np.array([res[m] for m in r.pool if test(m)])) for label, test in report.buckets(r).items()]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    y = np.arange(len(rows))[::-1]
    for yi, (label, x) in zip(y, rows):
        ax.plot([x.mean() - x.std(), x.mean() + x.std()], [yi, yi], color=OURS, lw=2, solid_capstyle='round')
        ax.scatter([x.mean()], [yi], s=40, color=INK, zorder=3, linewidths=0)
    ax.axvline(0, color=INK_2, lw=1)
    ax.set(yticks=y, yticklabels=[f'{l}  ({len(x)})' for l, x in rows], xlabel='model minus leaderboard',
           title='Where the model misses  ·  mean and 1 sd')
    ax.grid(axis='x')
    return fig


def plot_distribution(r):
    """Histogram coloured by difficulty, tier medians on top, and a strip of well-known charts
    underneath at their difficulty, in the same colours, to calibrate the scale by ear."""
    lib = np.array([r.pred[m] for m in r.library])
    lo, hi = np.percentile(lib, [0.5, 99.5])
    color_at = lambda x: TIER_CMAP(np.clip((x - lo) / (hi - lo), 0, 1))
    fig, (ax, ladder) = plt.subplots(1, 2, figsize=(17, 9), gridspec_kw={'width_ratios': [1.5, 1]})

    counts, edges = np.histogram(lib, bins=70)
    centers = (edges[:-1] + edges[1:]) / 2
    ax.bar(centers, counts, width=edges[1] - edges[0], color=[color_at(c) for c in centers], linewidth=0)
    top = counts.max()
    by_tier = collections.defaultdict(list)
    for lab, m in r.labels:
        if m in r.pred:
            by_tier[lab.tier].append(r.pred[m])
    for i, (tier, vals) in enumerate(sorted(by_tier.items())):
        x, lift = np.median(vals), 0.07 * (i % 2)       # alternate heights so close tiers don't collide
        ax.plot([x, x], [top * 1.02, top * (1.08 + lift)], color=INK_2, lw=1)
        ax.text(x, top * (1.1 + lift), f'T{tier}', ha='center', va='bottom', fontsize=9, color=INK_2)
    ax.text(edges[0], top * 1.1, 'DMT tier medians  ', ha='right', va='bottom', fontsize=9, color=INK_2)
    ax.set_ylim(0, top * 1.25)
    ax.set_xlim(edges[0] - 0.1, edges[-1] + 0.1)
    ax.set(title='Difficulty across the library', xlabel='difficulty', ylabel='charts')

    # ladder: one rung per difficulty band, its most-scored charts written beside it
    for lo_b, hi_b, ms in report.popular_by_band(r, bands=10, per_band=3):
        y = (lo_b + hi_b) / 2
        ladder.scatter([0], [y], s=90, color=color_at(y), edgecolors=SURFACE, linewidths=1.5, zorder=2)
        ladder.text(0.04, y, '\n'.join(r.name(m) for m in ms), va='center', fontsize=8.5, color=INK,
                    linespacing=1.3)
    ladder.axvline(0, color=GRID, lw=2, zorder=1)
    ladder.set_xlim(-0.05, 1)
    ladder.set_xticks([])
    ladder.spines['bottom'].set_visible(False)
    ladder.set(title='Popular charts at each difficulty', ylabel='difficulty')
    return fig


def plot_hardest(r, n=25):
    axes = active_axes(r)
    ms = sorted({**r.library, **r.anchors}, key=lambda m: -r.pred[m])[:n]
    lib = {a: np.sort([r.axes[a][m] for m in r.library]) for a in axes}
    n_lib = len(r.library)
    top = np.array([[max(n_lib - np.searchsorted(lib[a], r.axes[a][m]), 1) / n_lib for a in axes] for m in ms])
    # log of rarity, since the hardest charts sit in the top few percent on most axes
    rarity = -np.log10(top)
    sh = r.shares(ms)
    pct = 100 * np.array([sh[a] for a in axes]).T / np.maximum(sum(sh.values()), 1e-12)[:, None]
    fig, ax = plt.subplots(figsize=(11, 0.34 * n + 1.5))
    im = ax.imshow(rarity, cmap=RAMP, aspect='auto', vmin=0, vmax=3)
    for i in range(n):
        for j in range(len(axes)):
            ax.text(j, i, f'{pct[i, j]:.0f}%' if pct[i, j] >= 0.5 else '<1%', ha='center', va='center',
                    fontsize=8, color=SURFACE if rarity[i, j] > 1.8 else INK)
    ax.set_xticks(range(len(axes)), axes, rotation=30, ha='right')
    ax.set_yticks(range(n), [f'{r.pred[m]:4.1f}  ' + textwrap.fill(r.name(m), 50, subsequent_indent='       ')
                             for m in ms], fontsize=9)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    cb = fig.colorbar(im, ax=ax, shrink=0.5, ticks=[0, 1, 2, 3], label='axis score vs library')
    cb.ax.set_yticklabels(['all', 'top 10%', 'top 1%', 'top 0.1%'])
    cb.outline.set_visible(False)
    ax.set_title(f'Hardest {n} charts  ·  colour = rarity, number = % of the chart\'s score')
    return fig


def plot_axes(r):
    """Per axis across the library: thin line 5th to 95th percentile, bar 25th to 75th, dot at median."""
    sh = r.shares(list(r.library))
    total = sum(sh.values()).sum()
    axes = sorted(active_axes(r), key=lambda a: -sh[a].sum())
    fig, ax = plt.subplots(figsize=(10, 0.6 * len(axes) + 1.5))
    y = np.arange(len(axes))[::-1]
    for yi, a in zip(y, axes):
        p5, p25, p50, p75, p95 = np.percentile(sh[a], [5, 25, 50, 75, 95])
        ax.plot([p5, p95], [yi, yi], color=OURS, lw=1.5, solid_capstyle='round')
        ax.plot([p25, p75], [yi, yi], color=OURS, lw=9, solid_capstyle='butt')
        ax.scatter([p50], [yi], s=40, color=INK, zorder=3, linewidths=0)
        ax.text(p95, yi, f'   {sh[a].sum() / total:.0%}', va='center', fontsize=9, color=INK_2)
    ax.set(yticks=y, yticklabels=axes, xlabel=f'share of difficulty (all axes sum to difficulty {-r.model.intercept:+.2f})',
           title='What drives difficulty, per axis  ·  % = share of the library total')
    ax.set_xlim(left=0)
    ax.grid(axis='x')
    return fig


FEATURE_COLS = 6
FEATURE_BINS = 40
MIN_BIN_CHARTS = 5


def plot_features(r):
    """Every feature's spread across the library, one panel each, grouped by axis. Bar colour is
    the mean leaderboard difficulty of the scored charts in that bin, so a feature that tracks
    difficulty reads dark to bright left to right; ρ is its rank correlation with the leaderboard."""
    feats = [(a, k) for a, ks in AXES.items() for k in ks]
    lib = list(r.library)
    pool = r.pool
    lb_vals = np.array([r.fit.difficulty[m] for m in pool])
    lo_d, hi_d = np.percentile(lb_vals, [5, 95])
    rows = -(-len(feats) // FEATURE_COLS)
    fig, axs = plt.subplots(rows, FEATURE_COLS, figsize=(3.2 * FEATURE_COLS, 2.4 * rows))
    for ax, (axis, k) in zip(axs.flat, feats):
        x = np.array([r.features[m][k] for m in lib])
        lo, hi = np.percentile(x, [0.5, 99.5])
        if np.allclose(x, np.round(x)):
            # whole-number counts: one bin per value, or finer bins leave a comb of empty ones
            edges = np.arange(np.floor(lo), np.ceil(hi) + 2) - 0.5
        else:
            edges = np.linspace(lo, max(hi, lo + 1e-9), FEATURE_BINS + 1)
        counts, _ = np.histogram(np.clip(x, edges[0], edges[-1]), edges)
        xp = np.array([r.features[m][k] for m in pool])
        bin_of = np.clip(np.searchsorted(edges, xp, side='right') - 1, 0, len(counts) - 1)
        colors = []
        for b in range(len(counts)):
            sel = lb_vals[bin_of == b]
            colors.append(RAMP(0.25 + 0.75 * np.clip((sel.mean() - lo_d) / (hi_d - lo_d), 0, 1))
                          if len(sel) >= MIN_BIN_CHARTS else GRID)
        ax.bar(edges[:-1], counts, width=np.diff(edges), align='edge', color=colors, linewidth=0)
        ax.axvline(np.median(x), color=INK, lw=1, ls='--')
        ax.set_title(f'{axis} · {k}', fontsize=9, pad=4)
        ax.text(0.98, 0.95, f'ρ {spearmanr(xp, lb_vals)[0]:+.2f}\nzero {np.mean(x == 0):.0%}',
                transform=ax.transAxes, ha='right', va='top', fontsize=8, color=INK_2)
        ax.tick_params(labelsize=7)
        ax.set_yticks([])
    for ax in axs.flat[len(feats):]:
        ax.set_visible(False)
    fig.suptitle('Every feature across the library  ·  dashed = median, colour = mean leaderboard '
                 'difficulty in that bin (grey = too few scored charts)', x=0.01, ha='left', fontsize=12)
    return fig


PLOTS = {
    'tiers': plot_tiers,
    'tournaments': plot_tournaments,
    'model_vs_leaderboard': plot_model_vs_leaderboard,
    'residuals': plot_residuals,
    'distribution': plot_distribution,
    'hardest': plot_hardest,
    'axes': plot_axes,
    'features': plot_features,
}


PLOTS_DIR = pipeline.DATA / 'plots'


def latest_render():
    """The newest timestamped folder under PLOTS_DIR, or None."""
    return max((p for p in PLOTS_DIR.glob('*') if p.is_dir()), default=None)


def main(argv):
    render(pipeline.run(), argv)


def render(r, names=()):
    out = PLOTS_DIR / datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S')
    previous = latest_render()
    if names and previous:
        shutil.copytree(previous, out)    # re-rendering a few plots still leaves a complete set
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in PLOTS.items():
        if names and name not in names:
            continue
        fig = fn(r)
        fig.tight_layout()
        fig.savefig(out / f'{name}.png', dpi=130)
        plt.close(fig)
    if previous and same_plots(out, previous):
        shutil.rmtree(out)
        previous.rename(out)
        print(f'plots unchanged since {previous.name}, relabelled -> {out}')
    else:
        print(f'plots -> {out}')


def same_plots(a, b):
    files = sorted(p.name for p in a.iterdir())
    return files == sorted(p.name for p in b.iterdir()) and all(
        (a / f).read_bytes() == (b / f).read_bytes() for f in files)


if __name__ == '__main__':
    main(sys.argv[1:])
