"""Minimal Standard MIDI File reader: only what chart parsing needs."""
import struct
from dataclasses import dataclass, field
from pathlib import Path

META_TEXT_TYPES = range(0x01, 0x08)
META_TRACK_NAME = 0x03
META_TEMPO = 0x51
META_TIME_SIG = 0x58
META_END = 0x2F


@dataclass
class Track:
    name: str | None = None
    notes: list[tuple[int, int, int]] = field(default_factory=list)   # (tick, note, velocity), velocity 0 = off
    texts: list[tuple[int, str]] = field(default_factory=list)
    tempos: list[tuple[int, int]] = field(default_factory=list)       # (tick, us per quarter note)
    time_sigs: list[tuple[int, int, int]] = field(default_factory=list)


def _vlq(data, i):
    value = 0
    while True:
        byte = data[i]
        i += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, i


def _read_track(data):
    track = Track()
    tick = i = 0
    status = None
    while i < len(data):
        delta, i = _vlq(data, i)
        tick += delta
        byte = data[i]
        if byte == 0xFF:
            kind = data[i + 1]
            length, i = _vlq(data, i + 2)
            payload = data[i:i + length]
            i += length
            if kind == META_END:
                break
            if kind == META_TRACK_NAME and track.name is None:
                track.name = payload.decode('latin-1')
            elif kind in META_TEXT_TYPES:
                track.texts.append((tick, payload.decode('latin-1')))
            elif kind == META_TEMPO:
                track.tempos.append((tick, int.from_bytes(payload, 'big')))
            elif kind == META_TIME_SIG:
                track.time_sigs.append((tick, payload[0], 2 ** payload[1]))
            continue
        if byte in (0xF0, 0xF7):
            length, i = _vlq(data, i + 1)
            i += length
            continue
        if byte & 0x80:
            status = byte
            i += 1
        kind = status & 0xF0
        if kind in (0xC0, 0xD0):
            i += 1
            continue
        note, velocity = data[i], data[i + 1]
        i += 2
        if kind == 0x90:
            track.notes.append((tick, note, velocity))
        elif kind == 0x80:
            track.notes.append((tick, note, 0))
    return track


def read(path):
    """Returns (ticks per quarter note, [Track])."""
    data = Path(path).read_bytes()
    if data[:4] != b'MThd':
        raise ValueError(f'not a MIDI file: {path}')
    header_len = struct.unpack('>I', data[4:8])[0]
    _fmt, n_tracks, division = struct.unpack('>HHH', data[8:14])
    if division & 0x8000:
        raise ValueError(f'SMPTE timing not supported: {path}')
    i = 8 + header_len
    tracks = []
    while i + 8 <= len(data) and len(tracks) < n_tracks:
        length = struct.unpack('>I', data[i + 4:i + 8])[0]
        if data[i:i + 4] == b'MTrk':
            tracks.append(_read_track(data[i + 8:i + 8 + length]))
        i += 8 + length
    return division, tracks
