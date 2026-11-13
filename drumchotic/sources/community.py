"""Community difficulty claims (labels/community.txt): ordered groups of songs by one artist."""
import re
from dataclasses import dataclass
from pathlib import Path

PATH = Path(__file__).resolve().parent.parent / 'labels' / 'community.txt'
VARIANT = re.compile(r'\s*\(B\)\s*$', re.IGNORECASE)


@dataclass(frozen=True)
class Claim:
    artist: str
    source: str
    groups: tuple      # tuples of titles, hardest group first


def load(path=PATH):
    claims, head, groups = [], None, []
    for line in Path(path).read_text().splitlines() + ['@']:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if line.startswith('@'):
            if head:
                claims.append(Claim(*head, tuple(groups)))
            artist, _, source = line[1:].partition('|')
            head, groups = (artist.strip(), source.strip()), []
        else:
            groups.append(tuple(t.strip() for t in line.split(';') if t.strip()))
    return claims


def key(text):
    return VARIANT.sub('', text).strip().lower()


def pairs(claims, titles):
    """(claim, harder md5, easier md5) for every ordered pair the claims make, and the titles no
    library chart matched. titles: md5 -> 'artist - name'."""
    by_song = {}
    for m, t in titles.items():
        artist, _, name = t.partition(' - ')
        by_song.setdefault((artist.strip().lower(), key(name)), []).append(m)
    out, missing = [], []
    for c in claims:
        found = []
        for group in c.groups:
            ms = []
            for title in group:
                hit = by_song.get((c.artist.lower(), key(title)))
                ms += hit or []
                if not hit:
                    missing.append(f'{c.artist} - {title}')
            found.append(ms)
        for i, harder in enumerate(found):
            for easier in found[i + 1:]:
                out += [(c, h, e) for h in harder for e in easier]
    return out, missing
