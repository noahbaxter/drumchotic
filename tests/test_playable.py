import unittest

from drumchotic.chart.model import DrumChart, Hit, Pad, Span, TrackType
from drumchotic.measure.playable import playable


def chart(hits, rolls=()):
    return DrumChart('test', TrackType.FOUR_LANE, True, 480, hits, list(rolls))


class KickModeTests(unittest.TestCase):
    hits = [Hit(0, 0.0, Pad.KICK), Hit(120, 62.5, Pad.KICK, kick2x=True), Hit(240, 125.0, Pad.RED)]

    def test_2x_keeps_double_kicks(self):
        self.assertEqual(len(playable(chart(self.hits), kick_mode='2x')), 3)

    def test_1x_drops_double_kicks(self):
        kept = playable(chart(self.hits), kick_mode='1x')
        self.assertEqual([h.kick2x for h in kept if h.pad == Pad.KICK], [False])


class RollTests(unittest.TestCase):
    # eight snare hits inside a roll lane, a tom hit after it
    hits = [Hit(i * 60, i * 31.25, Pad.RED) for i in range(8)] + [Hit(600, 312.5, Pad.YELLOW)]
    roll = [Span(0.0, 250.0, 'roll1')]

    def test_half_keeps_every_other_note_in_the_lane(self):
        kept = playable(chart(self.hits, self.roll), roll_mode='half')
        self.assertEqual([h.tick for h in kept], [0, 120, 240, 360, 600])

    def test_skip_drops_the_lane(self):
        kept = playable(chart(self.hits, self.roll), roll_mode='skip')
        self.assertEqual([h.tick for h in kept], [600])

    def test_full_keeps_everything(self):
        self.assertEqual(len(playable(chart(self.hits, self.roll), roll_mode='full')), 9)


if __name__ == '__main__':
    unittest.main()
