import re
from pathlib import Path

from .model import DrumChart, Dynamic, Span
from .normalize import RawNote, disco_ranges, to_pro_drums, track_type
from .tempo import TempoMap

DEFAULT_RESOLUTION = 192
EXPERT_SECTION = 'ExpertDrums'

KICK = 0
HAND_LANES = range(1, 6)
KICK_2X = 32
ACCENT_BASE = 34   # 34-38 accent lanes 1-5
GHOST_BASE = 40    # 40-44 ghost lanes 1-5
CYMBAL_MARKERS = {66: 2, 67: 3, 68: 4}
ROLL_PHRASES = {65: 'roll1', 66: 'roll2'}

SECTION = re.compile(r'^\s*\[(.+?)\]\s*$')
EVENT = re.compile(r'^\s*(\d+)\s*=\s*(\w+)\s*(.*?)\s*$')
KEY_VALUE = re.compile(r'^\s*(\w+)\s*=\s*(.*?)\s*$')


def _sections(text):
    sections, name, body = {}, None, None
    for line in text.splitlines():
        m = SECTION.match(line)
        if m:
            name, body = m.group(1), []
            continue
        stripped = line.strip()
        if stripped == '{' or name is None:
            continue
        if stripped == '}':
            sections[name] = body
            name = None
            continue
        body.append(line)
    return sections


def _events(lines):
    for line in lines:
        m = EVENT.match(line)
        if m:
            yield int(m.group(1)), m.group(2), m.group(3)


def load(path, ini=None):
    """Expert drums from a notes.chart, or None if it has no ExpertDrums section."""
    ini = ini or {}
    sections = _sections(Path(path).read_text(encoding='utf-8-sig', errors='replace'))
    if EXPERT_SECTION not in sections:
        return None

    song = dict(m.groups() for m in map(KEY_VALUE.match, sections.get('Song', ())) if m)
    resolution = int(song.get('Resolution', DEFAULT_RESOLUTION))

    tempos, time_sigs = [], []
    for tick, kind, value in _events(sections.get('SyncTrack', ())):
        args = value.split()
        if kind == 'B':
            tempos.append((tick, 60_000_000_000 / int(args[0])))
        elif kind == 'TS':
            time_sigs.append((tick, int(args[0]), 2 ** int(args[1]) if len(args) > 1 else 4))
    tempo = TempoMap(tempos, resolution)

    notes, accents, ghosts, cymbals, rolls, mix = [], set(), set(), set(), [], []
    for tick, kind, value in _events(sections[EXPERT_SECTION]):
        args = value.split()
        if kind == 'N':
            lane = int(args[0])
            if lane == KICK or lane == KICK_2X or lane in HAND_LANES:
                notes.append((tick, lane))
            elif ACCENT_BASE <= lane < ACCENT_BASE + 5:
                accents.add((tick, lane - ACCENT_BASE + 1))
            elif GHOST_BASE <= lane < GHOST_BASE + 5:
                ghosts.add((tick, lane - GHOST_BASE + 1))
            elif lane in CYMBAL_MARKERS:
                cymbals.add((tick, CYMBAL_MARKERS[lane]))
        elif kind == 'S' and int(args[0]) in ROLL_PHRASES:
            rolls.append((tick, tick + int(args[1]), ROLL_PHRASES[int(args[0])]))
        elif kind == 'E':
            mix.append((tick, value.strip('"')))

    raw = []
    for tick, lane in notes:
        if lane in (KICK, KICK_2X):
            raw.append(RawNote(tick, 0, kick2x=lane == KICK_2X))
            continue
        dyn = Dynamic.ACCENT if (tick, lane) in accents else Dynamic.GHOST if (tick, lane) in ghosts else Dynamic.NORMAL
        # .chart 4-lane hands are toms unless a cymbal marker sits on them
        raw.append(RawNote(tick, lane, cymbal=(tick, lane) in cymbals, dynamic=dyn))

    ttype = track_type(ini, raw)
    pro_marked = bool(ini.get('pro_drums')) or bool(cymbals)
    return DrumChart(
        source=str(path),
        track_type=ttype,
        pro_marked=pro_marked,
        resolution=resolution,
        hits=to_pro_drums(raw, ttype, tempo, disco_ranges(mix) if pro_marked else ()),
        rolls=[Span(tempo.ms(a), tempo.ms(b), k) for a, b, k in sorted(rolls)],
        tempos=tempo.bpms(),
        time_sigs=time_sigs,
    )
