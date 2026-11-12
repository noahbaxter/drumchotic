import tempfile
import unittest
from pathlib import Path

from drumchotic.chart import parse_mid
from drumchotic.chart.model import Dynamic, Pad, TrackType
from tests.fixtures import note, text, write_mid

Q = 480  # .mid quarter note


def pads(chart):
    return [(h.tick, h.pad, h.cymbal) for h in chart.hits]


class MidTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / 'notes.mid'

    def tearDown(self):
        self.dir.cleanup()

    def load(self, events, ini=None, **kw):
        write_mid(self.path, events, **kw)
        return parse_mid.load(self.path, ini)

    def test_hands_default_to_cymbals_unless_tom_marked(self):
        chart = self.load(note(0, 98) + note(Q, 98) + note(Q, 110, length=10) + note(2 * Q, 97))
        self.assertEqual(pads(chart), [(0, Pad.YELLOW, True), (Q, Pad.YELLOW, False), (2 * Q, Pad.RED, False)])
        self.assertTrue(chart.pro_marked)
        self.assertEqual(chart.track_type, TrackType.FOUR_LANE)

    def test_tempo_change_moves_times(self):
        chart = self.load(note(0, 96) + note(Q, 96) + note(2 * Q, 96), extra_tempos=[(Q, 240.0)])
        self.assertEqual([round(h.time_ms) for h in chart.hits], [0, 500, 750])

    def test_kick_2x_and_shared_tick_kick(self):
        chart = self.load(note(0, 95) + note(Q, 96) + note(Q, 95))
        self.assertEqual([(h.tick, h.kick2x) for h in chart.kicks], [(0, True), (Q, False)])

    def test_five_lane_converts_to_pro(self):
        chart = self.load(note(0, 101) + note(Q, 100) + note(Q, 101) + note(2 * Q, 98))
        self.assertEqual(chart.track_type, TrackType.FIVE_LANE)
        self.assertEqual(pads(chart), [
            (0, Pad.GREEN, False),
            (Q, Pad.BLUE, False), (Q, Pad.GREEN, True),
            (2 * Q, Pad.YELLOW, True),
        ])

    def test_dynamics_need_enable_event(self):
        events = note(0, 97, vel=127) + note(Q, 97, vel=1)
        self.assertEqual([h.dynamic for h in self.load(events).hits], [Dynamic.NORMAL] * 2)
        chart = self.load(events + [(0, text('[ENABLE_CHART_DYNAMICS]'))])
        self.assertEqual([h.dynamic for h in chart.hits], [Dynamic.ACCENT, Dynamic.GHOST])

    def test_disco_flip_swaps_red_and_yellow_cymbal_on_pro(self):
        events = (note(0, 110, length=1) + [(Q, text('[mix 3 drums0d]')), (3 * Q, text('[mix 3 drums0]'))]
                  + note(Q, 97) + note(2 * Q, 98) + note(3 * Q, 97))
        chart = self.load(events)
        self.assertEqual(pads(chart), [(Q, Pad.YELLOW, True), (2 * Q, Pad.RED, False), (3 * Q, Pad.RED, False)])

    def test_rolls_and_flams(self):
        chart = self.load(note(0, 126, length=Q) + note(0, 97) + note(Q, 109, length=1) + note(Q, 99))
        self.assertEqual([(round(r.start_ms), round(r.end_ms), r.kind) for r in chart.rolls], [(0, 500, 'roll1')])
        self.assertEqual([h.flam for h in chart.hits], [False, True])

    def test_no_drum_track(self):
        write_mid(self.path, [])
        self.path.write_bytes(self.path.read_bytes().replace(b'PART DRUMS', b'PART BASS!'))
        self.assertIsNone(parse_mid.load(self.path))


if __name__ == '__main__':
    unittest.main()
