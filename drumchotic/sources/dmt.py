"""Drummer's Monthly tournament tiers: the folder a song sits in is its tier.

Tiers only order songs within one tournament (and its sudden death set), never across them.
"""
import re
from dataclasses import dataclass
from pathlib import Path

# themed rounds, not difficulty tiers
SKIP = ('Conquest Contenders', 'Clonpardy', 'Pro SD')
TIER = re.compile(r'(?:\bT|Tier\s*)(\d+)$')
SUDDEN_DEATH = re.compile(r'\bSD\b|Sudden Death')


@dataclass(frozen=True)
class Label:
    folder: Path
    group: str
    tier: int


def _label(song_dir, root):
    rel = song_dir.relative_to(root)
    if any(s in str(rel) for s in SKIP):
        return None
    parts = rel.parts
    tier_dir = parts[-2] if len(parts) >= 2 else ''
    m = TIER.search(tier_dir)
    if not m:
        return None
    group = parts[0]
    if any(SUDDEN_DEATH.search(p) for p in parts[1:-1]):
        group += ' / SD'
    return Label(song_dir, group, int(m.group(1)))


def load(root):
    root = Path(root)
    labels = (_label(ini.parent, root) for ini in sorted(root.rglob('song.ini')))
    return [l for l in labels if l]
