"""Score how rare each chart's note patterns are against the whole library.

python -m drumchotic.tools.build_rarity

Runs after build_features: it takes the chart folders from the feature caches and writes
data/cache/rarity.json (md5 -> rarity features) and data/cache/rarity_table.npz (how many artists
play each run, for rating charts outside the library). Leaderboard and tournament charts make up
the table; anchors are scored against it without counting toward it. Skips the work when no
feature cache changed.
"""
import collections
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from ..chart import song
from ..measure import rarity

CACHE = Path('data/cache')
TABLE_SETS = ('features', 'features_dmt')
SETS = (*TABLE_SETS, 'features_anchors')
OUT, TABLE, KEY = CACHE / 'rarity.json', CACHE / 'rarity_table.npz', CACHE / 'rarity.key'


def one(job):
    md5, folder = job
    try:
        chart, meta = song.load(folder)
        return md5, rarity.artist(meta), *rarity.runs(chart)
    except Exception:
        return md5, None, None, None


def main():
    present = [s for s in SETS if (CACHE / f'{s}.json').exists()]
    key = '|'.join((CACHE / f'{s}.key').read_text() for s in present) + Path(__file__).read_text()
    if OUT.exists() and TABLE.exists() and KEY.exists() and KEY.read_text() == key:
        print(f'{OUT} up to date')
        return
    folders, in_table = {}, set()
    for s in present:
        for m, e in json.loads((CACHE / f'{s}.json').read_text()).items():
            folders[m] = e['folder']
            if s in TABLE_SETS:
                in_table.add(m)
    with ProcessPoolExecutor() as ex:
        runs = [r for r in ex.map(one, folders.items(), chunksize=32) if r[1] is not None]
    by_artist = collections.defaultdict(list)
    for m, a, _, h in runs:
        if m in in_table:
            by_artist[a].append(h)
    table = rarity.Table.build(by_artist)
    out = {m: dict(rarity.EMPTY) for m in folders}
    out.update({m: rarity.features(t, h, table, m in in_table) for m, _, t, h in runs})
    OUT.write_text(json.dumps(out))
    table.save(TABLE)
    KEY.write_text(key)
    print(f'{len(table.hashes)} runs over {table.artists} artists, {len(folders) - len(runs)} charts unreadable -> {OUT}')


if __name__ == '__main__':
    main()
