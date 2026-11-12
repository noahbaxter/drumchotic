"""Per-axis scorecard: how well each axis predicts on its own, and what the model loses without it.
Every variant is refit on the pipeline's own folds, so the numbers compare directly.

python -m drumchotic.audit
"""
from concurrent.futures import ProcessPoolExecutor

from scipy.stats import spearmanr

from . import pipeline
from .fit.metrics import tier_accuracy
from .tuning import AXES


def evaluate(r, configs):
    """configs: {name: {axis: [features]}} -> {name: (held-out Spearman, DMT tier accuracy)}."""
    F, d, nsc, pool = r.features, r.fit.difficulty, r.fit.n_scores, r.pool
    sets = pipeline.held_out_sets(pool, {m for _, m in r.labels})
    lib = list(r.library)
    jobs = []
    for axes in configs.values():
        keys = [k for ks in axes.values() for k in ks]
        for ms in sets:
            jobs.append(([{k: F[m][k] for k in keys} for m in ms], [d[m] for m in ms], [nsc[m] for m in ms], axes))
    with ProcessPoolExecutor() as ex:
        models = list(ex.map(pipeline.train, jobs))
    out = {}
    for i, name in enumerate(configs):
        *folds, no_dmt = models[i * len(sets):(i + 1) * len(sets)]
        held = pipeline.predict_held_out(folds, pool, F)
        sp = spearmanr([d[m] for m in pool], [held[m] for m in pool])[0]
        out[name] = (sp, tier_accuracy(r.labels, dict(zip(lib, no_dmt.predict([F[m] for m in lib])))))
    return out


def main():
    r = pipeline.run()
    configs = {'all axes': AXES}
    configs.update({f'{a} alone': {a: AXES[a]} for a in AXES})
    configs.update({f'without {a}': {b: ks for b, ks in AXES.items() if b != a} for a in AXES})
    res = evaluate(r, configs)
    sp_sd, tier_sd = r.noise()
    full_sp, full_tiers = res['all axes']
    print(f'all axes: leaderboard Spearman {full_sp:.3f} (noise sd {sp_sd:.3f}), '
          f'DMT tiers {full_tiers:.3f} (noise sd {tier_sd:.3f})\n')
    print(f'{"axis":13} {"alone: Spearman":>16} {"tiers":>6}   {"without it: Δ Spearman":>23} {"Δ tiers":>8}')
    for a in sorted(AXES, key=lambda a: -res[f'{a} alone'][0]):
        sp, ti = res[f'{a} alone']
        wsp, wti = res[f'without {a}']
        print(f'{a:13} {sp:16.3f} {ti:6.3f}   {wsp - full_sp:+23.3f} {wti - full_tiers:+8.3f}')


if __name__ == '__main__':
    main()
