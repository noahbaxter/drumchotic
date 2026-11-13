from . import smf
from .model import DrumChart, Dynamic, Span
from .normalize import RawNote, disco_ranges, in_ranges, to_pro_drums, track_type
from .tempo import TempoMap

DRUM_TRACK_NAMES = ('PART DRUMS', 'PART DRUM')

EXPERT_KICK_2X = 95
EXPERT_KICK = 96
EXPERT_LANES = range(97, 102)  # red .. 5-lane green
FLAM = 109
TOM_MARKERS = {110: 2, 111: 3, 112: 4}  # marker note -> lane it turns into a tom
ROLL_MARKERS = {126: 'roll1', 127: 'roll2'}

ACCENT_VELOCITY = 127
GHOST_VELOCITY = 1
DYNAMICS_EVENT = 'ENABLE_CHART_DYNAMICS'


def _spans(notes, pitch):
    """Pairs note-ons with the next note-off of that pitch: [start, end) ticks."""
    spans, start = [], None
    for tick, note, vel in notes:
        if note != pitch:
            continue
        if vel > 0 and start is None:
            start = tick
        elif vel == 0 and start is not None:
            spans.append((start, tick))
            start = None
    return spans


def load(path, ini=None):
    """Expert drums from a notes.mid, or None if it has no drum track."""
    ini = ini or {}
    resolution, tracks = smf.read(path)
    drums = next((t for t in tracks if t.name and t.name.strip().upper() in DRUM_TRACK_NAMES), None)
    if drums is None:
        return None

    conductor = tracks[0]
    tempo = TempoMap(conductor.tempos, resolution)
    # sort so a note-off sharing a tick with the next note-on closes the old span first
    notes = sorted(drums.notes, key=lambda n: (n[0], n[2] > 0))
    toms = {lane: _spans(notes, pitch) for pitch, lane in TOM_MARKERS.items()}
    flams = _spans(notes, FLAM)
    dynamics = any(DYNAMICS_EVENT in text for _, text in drums.texts)

    raw = []
    for tick, note, vel in notes:
        if vel == 0:
            continue
        if note in (EXPERT_KICK, EXPERT_KICK_2X):
            raw.append(RawNote(tick, 0, kick2x=note == EXPERT_KICK_2X))
        elif note in EXPERT_LANES:
            lane = note - EXPERT_LANES.start + 1
            dyn = Dynamic.NORMAL
            if dynamics and vel == ACCENT_VELOCITY:
                dyn = Dynamic.ACCENT
            elif dynamics and vel == GHOST_VELOCITY:
                dyn = Dynamic.GHOST
            # .mid 4-lane hands are cymbals unless a tom marker covers them
            cymbal = not in_ranges(tick, toms.get(lane, ()))
            raw.append(RawNote(tick, lane, cymbal=cymbal, dynamic=dyn, flam=in_ranges(tick, flams)))

    ttype = track_type(ini, raw)
    pro_marked = bool(ini.get('pro_drums')) or any(toms.values())
    rolls = [Span(tempo.ms(a), tempo.ms(b), kind)
             for pitch, kind in ROLL_MARKERS.items() for a, b in _spans(notes, pitch)]
    return DrumChart(
        source=str(path),
        track_type=ttype,
        pro_marked=pro_marked,
        resolution=resolution,
        hits=to_pro_drums(raw, ttype, tempo, disco_ranges(drums.texts) if pro_marked else ()),
        rolls=sorted(rolls, key=lambda s: s.start_ms),
        tempos=tempo.bpms(),
        time_sigs=conductor.time_sigs,
    )
