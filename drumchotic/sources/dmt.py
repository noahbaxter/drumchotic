"""Drummer's Monthly tournament tiers: the folder a song sits in is its tier.

Tiers only order songs within one tournament, never across them. A sudden death set's tiers are
the same as its tournament's (armchairsum65), so its songs join the tournament's tiers.
"""
import re
from dataclasses import dataclass
from pathlib import Path

# themed rounds, not difficulty tiers; Icebreaker 2023's Pro SD isn't tiered and varies a lot
SKIP = ('Conquest Contenders', 'Clonpardy', 'Pro SD')
TIER = re.compile(r'(?:\bT|Tier\s*)(\d+)$')
# Tiers mean the same thing across tournaments from this year on. Older ones (and undated ones,
# like BirdmanExe) numbered their tiers their own way: they still order their own songs, but stay
# out of anything that pools tiers across tournaments. Checked 2026-11-11: armchairsum65's
# renumbering of Birdman and Summer Blast 2023 lands on the same tier medians as this cut.
LADDER_FROM = 2024
YEAR = re.compile(r'\b(20\d\d)\b')


@dataclass(frozen=True)
class Label:
    folder: Path
    group: str
    tier: int          # as the tournament named it

    @property
    def modern(self):
        """The tier on today's ladder, for comparing across tournaments; None before LADDER_FROM."""
        m = YEAR.search(self.group)
        return self.tier if m and int(m.group(1)) >= LADDER_FROM else None


def _label(song_dir, root):
    rel = song_dir.relative_to(root)
    if any(s in str(rel) for s in SKIP):
        return None
    parts = rel.parts
    tier_dir = parts[-2] if len(parts) >= 2 else ''
    m = TIER.search(tier_dir)
    if not m:
        return None
    return Label(song_dir, parts[0], int(m.group(1)))


def load(root):
    root = Path(root)
    labels = (_label(ini.parent, root) for ini in sorted(root.rglob('song.ini')))
    return [l for l in labels if l]
