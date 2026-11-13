"""Where in a chart each axis peaks, with the notes at that spot, to check an axis against the chart.

python -m drumchotic.tools.explain "kick burst" [--top N]  the N charts hardest on that axis, peak section of each
python -m drumchotic.tools.explain --chart "orb weaver"     every axis's peak for charts whose title matches
"""
import sys

import numpy as np

from ..chart import song
from ..measure import features, rarity, sticking
from ..measure.playable import playable
from ..measure.timing import fastest_run_at, window_sums
from ..pipeline import load_features, rarity_table
from ..tuning import AXES, DENSITY_BEATS, ENDURANCE_NPS, SPEED_WINDOW_S

ENDURANCE_SHOWN = ENDURANCE_NPS[len(ENDURANCE_NPS) // 2]
BURST_SHOWN, STAMINA_SHOWN = 8, 32
LIMBS = {'kick': ('kick', 'kicks'), 'hand': ('hands', 'hand notes'), 'one hand': ('onehand', 'hits on one hand')}
# per axis: the cached feature that ranks it, and the unit of the spot shown
HEADLINE = {
    'speed': ('max_nps', f'notes in the busiest {SPEED_WINDOW_S}s'),
    'density': ('density_p50', f'notes/s in a typical {DENSITY_BEATS}-beat chunk (the chart median, repeats discounted)'),
    'endurance': (f'endurance_longest_n{ENDURANCE_SHOWN}',
                  f'seconds in the longest unbroken stretch at {ENDURANCE_SHOWN}+ notes/s'),
    'movement': ('travel_w4', 'kit distance moved per second, densest 4s'),
    'sticking': ('sticking_w4', 'cost of the easiest sticking per second, densest 4s'),
    'linear': ('linear_w4', 'kick/drum alternations per second (cymbals on top allowed), densest 4s'),
    'coordination': ('coord_offbeat_w4', 'per second, the lesser of kicks and hand notes off the 8th grid, densest 4s'),
    'variety': ('limb_novel_w4', 'new limb orders per second, densest 4s'),
    'dynamics': ('dynamics_w4', 'accents and ghosts per second, densest 4s'),
    'rare patterns': ('rarity_w4', 'rarity of the runs played (few other artists play them) per second, densest 4s'),
}
for _label, (_key, _unit) in LIMBS.items():
    HEADLINE[f'{_label} burst'] = (f'run{BURST_SHOWN}_{_key}', f'{_unit}/s over the fastest {BURST_SHOWN}')
    HEADLINE[f'{_label} stamina'] = (f'run{STAMINA_SHOWN}_{_key}', f'{_unit}/s over the fastest {STAMINA_SHOWN}')
    HEADLINE[f'{_label} syncopation'] = (f'{_key}_offbeat_w4', f'{_unit} off the 8th grid per second, densest 4s')
WINDOW_S = 4
DUMP_LINES = 32


def _window_peak(t, sums, window_s=WINDOW_S):
    if len(t) == 0:
        return 0.0, 0.0, 0.0
    i = int(np.argmax(sums))
    return float(sums[i]), float(t[i]), float(t[i]) + window_s * 1000


def _typical_chunk(nps, start, end):
    """(notes/s, start ms, end ms) of the chunk whose density sits closest to the chart's median."""
    i = int(np.argmin(np.abs(nps - features.weighted_quantile(nps, end - start, 0.5))))
    return float(nps[i]), float(start[i]), float(end[i])


def _longest_hot(nps, start, end):
    """(seconds, start ms, end ms) of the longest back-to-back run of chunks at ENDURANCE_SHOWN+ notes/s."""
    best, run_start, prev_end = (0.0, 0.0, 0.0), None, None
    for n, s, e in zip(nps, start, end):
        if n < ENDURANCE_SHOWN:
            run_start = None
        elif run_start is None or not np.isclose(s, prev_end):
            run_start = s
        if run_start is not None and (e - run_start) / 1000.0 > best[0]:
            best = ((e - run_start) / 1000.0, float(run_start), float(e))
        prev_end = e
    return best


def peaks(chart):
    """{axis: (value, start ms, end ms)} for each axis's headline measure."""
    hits = playable(chart)
    o = features.Onsets.of(hits)
    strokes = features.strokes_of(o)
    mt, dist, switch = features.moves(strokes, dict(zip(o.t, o.weight)))
    ws = lambda t, w, s=WINDOW_S: window_sums(t, w, s)
    hands = features.hand_times(strokes)
    nt = features.note_times(hits)
    st, st_cost = features.sticking_series(strokes)
    ch = features.chunks(hits, chart, features.repeat_weights(hits, o))
    res = chart.resolution
    tick_at = dict(zip(o.t, o.ticks))
    run_t, run_h = rarity.runs(chart)
    run_t = run_t[:len(run_h)]
    limb_times = {
        'kick': [o.t[o.has_kick]],
        'hand': [o.t[o.has_hand]],
        'one hand': list(hands.values()),
    }
    out = {
        'speed': _window_peak(nt, ws(nt, np.ones(len(nt)), SPEED_WINDOW_S), SPEED_WINDOW_S),
        'density': _typical_chunk(*ch),
        'endurance': _longest_hot(*ch),
        'movement': _window_peak(mt, ws(mt, dist)),
        'sticking': _window_peak(st, ws(st, st_cost)),
        'linear': _window_peak(o.t, ws(o.t, features.linear_series(o))),
        'coordination': _window_peak(o.t, features.coordination_series(o, res, WINDOW_S)['offbeat']),
        'variety': _window_peak(o.t, ws(o.t, features.limb_order_series(o, strokes))),
        'dynamics': _window_peak(o.t, ws(o.t, o.dynamics)),
        'rare patterns': _window_peak(run_t, ws(run_t, rarity_table().rarity(run_h, in_table=True))),
    }
    for label, times in limb_times.items():
        out[f'{label} burst'] = max((fastest_run_at(t, BURST_SHOWN) for t in times), key=lambda p: p[0])
        out[f'{label} stamina'] = max((fastest_run_at(t, STAMINA_SHOWN) for t in times), key=lambda p: p[0])
        out[f'{label} syncopation'] = max(
            (_window_peak(t, ws(t, features.off_grid([tick_at[x] for x in t], res))) for t in times),
            key=lambda p: p[0])
    return out


def clock(ms):
    return f'{int(ms // 60000)}:{ms % 60000 / 1000:06.3f}'


def dump(chart, start, end):
    """The notes between start and end, one onset per line: time, gap, kick, hand surfaces (with hand)."""
    o = features.Onsets.of(playable(chart))
    strokes = features.strokes_of(o)
    hand_at = {}
    for s in strokes:
        hand_at.setdefault(s.time_ms, []).append(f"{sticking.SURFACES[s.surface][0]}{'LR'[s.hand]}")
    lines, prev = [], None
    for i in np.where((o.t >= start - 1) & (o.t <= end + 1))[0]:
        t = o.t[i]
        gap = f'+{t - prev:4.0f}' if prev is not None else '     '
        lines.append(f'    {clock(t)} {gap}  {"K" if o.has_kick[i] else " "}  {" ".join(hand_at.get(t, []))}')
        prev = t
    if len(lines) > DUMP_LINES:
        lines = lines[:DUMP_LINES] + [f'    ... {len(lines) - DUMP_LINES} more onsets']
    return '\n'.join(lines)


def show(entry, axes):
    chart, _ = song.load(entry['folder'])
    p = peaks(chart)
    print(f"\n{entry.get('title', entry['folder'])}")
    for a in axes:
        value, start, end = p[a]
        print(f'  {a}: {value:.1f} ({HEADLINE[a][1]}) at {clock(start)}-{clock(end)}')
        if len(axes) == 1:
            print(dump(chart, start, end))


def main(argv):
    cache = load_features('features.json', 'features_dmt.json', 'features_anchors.json')
    if '--chart' in argv:
        q = argv[argv.index('--chart') + 1].lower()
        for e in cache.values():
            if q in e.get('title', e['folder']).lower():
                show(e, list(AXES))
        return
    axis = argv[0]
    top = int(argv[argv.index('--top') + 1]) if '--top' in argv else 5
    key = HEADLINE[axis][0]
    for e in sorted(cache.values(), key=lambda e: -e['features'][key])[:top]:
        show(e, [axis])


if __name__ == '__main__':
    main(sys.argv[1:])
