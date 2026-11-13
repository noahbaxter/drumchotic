"""Compute features for every chart folder under a root, keyed by chart md5.

python -m drumchotic.tools.build_features data/charts data/cache/features.json [--force]

Skips the work when the charts, the measuring code and the FEATURES/STICKING
knobs are all unchanged since the last build.
"""
import hashlib
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from .. import tuning
from ..chart import song
from ..measure import features

PACKAGE = Path(__file__).parent.parent


def build_key(folders):
    """What a feature cache depends on: chart files, measuring code, measuring knobs."""
    h = hashlib.sha1()
    knobs = Path(tuning.__file__).read_text().split('# ---- COMBINE')[0]
    h.update(knobs.encode())
    for p in sorted([*PACKAGE.glob('chart/*.py'), *PACKAGE.glob('measure/*.py'), Path(__file__)]):
        h.update(p.read_bytes())
    for folder in folders:
        for name in ('song.ini', *song.NOTE_FILES):
            p = Path(folder) / name
            if p.exists():
                st = p.stat()
                h.update(f'{p}|{st.st_size}|{st.st_mtime_ns}'.encode())
    return h.hexdigest()


def one(folder):
    folder = Path(folder)
    try:
        chart, meta = song.load(folder)
        f = features.compute(chart) if chart else None
    except Exception as e:
        return None, f'{folder}: {type(e).__name__}: {e}'
    if f is None:
        return None, None
    return (song.md5(folder), {'folder': str(folder), 'title': song.title(meta, folder),
                               'features': {k: float(v) for k, v in f.items()}}), None


def main(argv):
    root, out = Path(argv[0]), Path(argv[1])
    folders = sorted({str(p.parent) for p in root.rglob('song.ini')})
    key, key_file = build_key(folders), out.with_suffix('.key')
    if '--force' not in argv and out.exists() and key_file.exists() and key_file.read_text() == key:
        print(f'{out} up to date')
        return
    result, errors = {}, []
    # hand assignments are cached per chart next to the feature caches (see features.strokes_of)
    with ProcessPoolExecutor(initializer=features.use_stroke_cache, initargs=(out.parent / 'strokes',)) as ex:
        for row, err in ex.map(one, folders, chunksize=16):
            if err:
                errors.append(err)
            if row:
                md5, entry = row
                result[md5] = entry
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result))
    key_file.write_text(key)
    print(f'{len(result)} charts, {len(errors)} errors -> {out}')
    for e in errors[:10]:
        print(e)


if __name__ == '__main__':
    main(sys.argv[1:])
