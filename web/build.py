"""Explorer page: the library as filterable plots and a table, one self-contained HTML file.

scripts/web.sh         writes data/web/index.html (and data.json) and opens it
scripts/serve.sh       serves it locally, reloading on changes
"""
import collections
import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np

from drumchotic.chart import ini
from drumchotic.rating import PEERS, REASONS_SHOWN, STANDS_OUT, Rater, charter_rating, library_title
from drumchotic.tuning import AXES

OUT = Path(__file__).resolve().parent.parent / 'data' / 'web' / 'index.html'
DATA = OUT.with_name('data.json')
TEMPLATE = Path(__file__).with_name('template.html')
# song.ini fields the search box matches (not shown on the page); 'frets' is the old name for charter
SEARCHED = ('artist', 'name', 'album', 'charter', 'frets', 'genre', 'year', 'playlist', 'sub_playlist')
TAG = re.compile(r'<[^>]*>')   # Clone Hero colour/format tags in charter names
RESULTS = OUT.parent.parent / 'results'
STARTED = re.compile(r'started (\w+ \d+, \d{4})')   # in the scraped Challonge standings headers


def tournament_dates():
    """{tournament folder name: first bracket's start date, YYYY-MM-DD} from data/results."""
    dates = {}
    for d in RESULTS.iterdir() if RESULTS.exists() else ():
        found = [datetime.strptime(m.group(1), '%B %d, %Y') for f in d.glob('*.txt') if (m := STARTED.search(f.read_text()))]
        if found:
            dates[d.name] = f'{min(found):%Y-%m-%d}'
    return dates


def search_text(folder):
    meta = ini.read(Path(folder) / 'song.ini')
    return ' '.join(TAG.sub('', str(meta[k])) for k in SEARCHED if meta.get(k)).lower()


def peer_reasons(rater):
    """Per chart: indexes of the axes where it beats STANDS_OUT% of charts at its level, best first."""
    order, vals = rater.order, rater.lib_axes
    out = [None] * len(order)
    for pos, i in enumerate(order):
        peers = order[max(0, pos - PEERS):pos + PEERS]
        pct = (vals[:, peers] < vals[:, [i]]).mean(1) * 100
        best = [a for a in np.argsort(-pct) if pct[a] >= STANDS_OUT]
        out[i] = [int(a) for a in best[:REASONS_SHOWN]]
    return out


def build():
    rater = Rater()
    r = rater.r
    lib = rater.lib
    axes = list(AXES)
    sh = r.shares(lib)
    why = peer_reasons(rater)
    tiers = collections.defaultdict(list)
    for lab, m in r.labels:
        tiers[m].append([lab.group, lab.tier])
    pool = set(r.pool)
    charts = []
    for i, m in enumerate(lib):
        artist, title = library_title(r, m)
        rated = charter_rating(r.library[m]['folder'])
        charts.append({
            'a': artist, 't': title, 's': search_text(r.library[m]['folder']),
            'd': round(float(r.pred[m]), 3),
            'lv': round(rater.level(r.pred[m]), 2),
            'ch': round(rater.charter(r.pred[m]), 2),
            'r': rated if rated >= 0 else None,
            'lb': round(float(r.fit.difficulty[m]), 3) if m in pool else None,
            'ho': round(float(r.held_out[m]), 3) if m in pool else None,
            'n': int(r.fit.n_scores.get(m, 0)),
            'tn': tiers.get(m, []),
            'sh': [round(float(sh[a][i]), 3) for a in axes],
            'why': why[i],
        })
    groups = sorted({g for v in tiers.values() for g, _ in v})
    medians = [[int(t), round(rater.charter(v), 3)] for t, v in zip(rater.level.levels, rater.level.medians)]
    data = {'axes': axes, 'groups': groups, 'charts': charts, 'tierMedians': medians, 'started': tournament_dates(),
            'built': f'{datetime.now():%Y-%m-%d}'}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(data, separators=(',', ':')))
    OUT.write_text(page())
    print(OUT)


def page():
    """The template with the last built data baked in."""
    return TEMPLATE.read_text().replace('/*DATA*/null', DATA.read_text())


if __name__ == '__main__':
    build()
