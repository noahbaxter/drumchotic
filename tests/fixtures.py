"""Builds tiny .mid/.chart files for parser tests."""
import struct


def _vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def _track(events):
    """events: (tick, bytes). Sorted, delta-encoded, end-of-track appended."""
    body, last = b'', 0
    for tick, data in sorted(events, key=lambda e: e[0]):
        body += _vlq(tick - last) + data
        last = tick
    body += _vlq(0) + b'\xff\x2f\x00'
    return b'MTrk' + struct.pack('>I', len(body)) + body


def meta(kind, payload):
    return bytes([0xFF, kind]) + _vlq(len(payload)) + payload


def name(text):
    return meta(0x03, text.encode())


def text(t):
    return meta(0x01, t.encode())


def tempo(bpm):
    return meta(0x51, round(60_000_000 / bpm).to_bytes(3, 'big'))


def on(note, vel=100):
    return bytes([0x90, note, vel])


def off(note):
    return bytes([0x80, note, 0])


def note(tick, pitch, length=1, vel=100):
    return [(tick, on(pitch, vel)), (tick + length, off(pitch))]


def write_mid(path, drum_events, resolution=480, bpm=120.0, extra_tempos=()):
    conductor = [(0, name('tempo')), (0, tempo(bpm))] + [(t, tempo(b)) for t, b in extra_tempos]
    drums = [(0, name('PART DRUMS'))] + drum_events
    header = b'MThd' + struct.pack('>IHHH', 6, 1, 2, resolution)
    path.write_bytes(header + _track(conductor) + _track(drums))
