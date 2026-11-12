"""Challonge bracket standings pasted into data/results/<tournament>/*.txt.

Each standings row is `rank<TAB>participant<TAB>...`; the next columns may
hold a style tag (H/B/K), the Challonge account, match history or totals.
Players are resolved to DMBot usernames via discord-names.tsv, then by
lowercased alphanumeric match; anyone else keeps a `challonge:` key.
"""
import re
from dataclasses import dataclass
from pathlib import Path

STYLE = re.compile(r'[HBK]')
NOT_A_NAME = re.compile(r'[HBK]|[\d-]+|[WL ]+')


def norm(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())


@dataclass(frozen=True)
class Entry:
    rank: int
    player: str      # DMBot username, or challonge:<name>
    style: str       # H, B, K or ''


@dataclass(frozen=True)
class Bracket:
    tournament: str
    kind: str
    entries: tuple


def _aliases(path):
    out = {}
    if path.exists():
        for line in path.read_text().splitlines():
            if line and not line.startswith('#'):
                a, b = line.split('\t')
                out[norm(a)] = b
    return out


def load(root, usernames):
    root = Path(root)
    alias = _aliases(root / 'discord-names.tsv')
    known = {norm(u): u for u in usernames}

    def resolve(cands):
        for c in cands:
            n = norm(c)
            if n in alias:
                return alias[n]
            if n in known:
                return known[n]
        return 'challonge:' + cands[0]

    brackets = []
    for p in sorted(root.rglob('*standings.txt')):
        entries = []
        for line in p.read_text().splitlines():
            cols = line.split('\t')
            if len(cols) < 2 or not cols[0].isdigit():
                continue
            style = cols[2] if len(cols) > 2 and STYLE.fullmatch(cols[2]) else ''
            cands = [c for c in cols[1:4] if c and not NOT_A_NAME.fullmatch(c)]
            entries.append(Entry(int(cols[0]), resolve(cands), style))
        kind = p.stem.removeprefix('challonge').removesuffix('standings').strip('-') or 'main'
        brackets.append(Bracket(p.parent.name, kind, tuple(entries)))
    return brackets


def pairs(brackets):
    """(winner, loser, weight) for every pair of finishers in a bracket,
    weighted so each bracket counts once per player rather than per pair."""
    out = []
    for b in brackets:
        n = len(b.entries)
        for i, a in enumerate(b.entries):
            for c in b.entries[i + 1:]:
                if a.rank != c.rank:
                    w, l = (a, c) if a.rank < c.rank else (c, a)
                    out.append((w.player, l.player, 1.0 / (n - 1)))
    return out
