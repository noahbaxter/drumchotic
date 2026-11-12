"""Staycation44's fretwork difficulty spreadsheets, from fretwork run on our own chart copies
(scripts/run_fretwork.sh writes them to data/references/fretwork_local/).

Drum rows carry D_1x / D_2x (fretwork's raw difficulty). The sheets have no md5
or path, so charts match by artist + title; titles shared by different charts
are dropped rather than guessed.
"""
import re
from collections import defaultdict
from pathlib import Path


def key(artist, title):
    """Keeps (...) and [...], which tells '(2x)' from '(4x)' charts of the same song."""
    def norm(s):
        return re.sub(r'[^a-z0-9]', '', str(s or '').lower())
    return norm(artist) + '|' + norm(title)


def load_drums(root):
    """key -> fretwork D for Expert drums (2x kick when the chart has it)."""
    import openpyxl
    seen = defaultdict(set)
    for path in sorted(Path(root).glob('*.xlsx')):
        rows = openpyxl.load_workbook(path, read_only=True)['Drums'].iter_rows(values_only=True)
        header = next(rows)
        for row in rows:
            r = dict(zip(header, row))
            d = r['D_2x'] if r['D_2x'] is not None else r['D_1x']
            if r['Level'] == 'Expert' and d is not None:
                seen[key(r['Artist'], r['Song Title'])].add(d)
    return {k: next(iter(v)) for k, v in seen.items() if len(v) == 1}


def by_md5(root, entries):
    """md5 -> fretwork D for our charts, matched on each chart's own song.ini artist and name
    (what fretwork itself reads). entries: md5 -> {'folder': ...} from the feature cache."""
    from ..chart import ini
    scores = load_drums(root)
    out = {}
    for md5, e in entries.items():
        meta = ini.read(Path(e['folder']) / 'song.ini')
        k = key(meta.get('artist'), meta.get('name'))
        if k in scores:
            out[md5] = scores[k]
    return out
