"""Official Rock Band drum tiers (0 warmup to 6 devils) for the library's Rock Band charts: the disc
games and DLC, charted by Harmonix, each folder's song.ini diff_drums.

The Beatles: Rock Band is left out: its tiers rank its own setlist, which is easy throughout
(agreement with the model 0.44 against 0.75 for the rest). Disc and DLC agree up to tier 4; disc
tiers 5 and 6 sit lower, since each disc fills every tier for career mode.
"""
from dataclasses import dataclass
from pathlib import Path

from ..chart import ini

FOLDER = 'Rock Band'
SKIP = ('Beatles',)
TIERS = range(7)


@dataclass(frozen=True)
class Label:
    md5: str
    tier: int
    source: str        # the game or DLC folder, e.g. 'Rock Band 2 DLC'


def source_of(folder):
    """The game or DLC folder a chart sits in, if it sits in the Rock Band folder."""
    parts = Path(folder).parts
    if FOLDER not in parts[:-1]:
        return None
    src = parts[parts.index(FOLDER) + 1]
    return src.split(') ', 1)[1] if src.startswith('(') else src


def load(library):
    """[Label] for library charts (md5 -> {'folder', ...}) from an official Rock Band game or DLC."""
    out = []
    for m, e in library.items():
        src = source_of(e['folder'])
        if not src or any(s in src for s in SKIP):
            continue
        meta = ini.read(Path(e['folder']) / 'song.ini')
        if 'harmonix' not in str(meta.get('charter', meta.get('frets', ''))).lower():
            continue
        try:
            tier = int(float(meta.get('diff_drums', -1)))
        except ValueError:
            continue
        if tier in TIERS:
            out.append(Label(m, tier, src))
    return out
