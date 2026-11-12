import unittest

from drumchotic.chart.model import DrumChart, Hit, Pad, TrackType
from drumchotic.measure import features

RES = 480                  # ticks per quarter note
SIXTEENTH = RES // 4       # 125 ms at 120 BPM
MS_PER_TICK = 500.0 / RES


def chart(hits):
    return DrumChart('test', TrackType.FOUR_LANE, True, RES, hits, tempos=[(0, 120.0)])


def hit(tick, pad, cymbal=False):
    return Hit(tick, tick * MS_PER_TICK, pad, cymbal)


def groove(start_tick, bars):
    """Hi-hat 8ths, kick on 1 and 3, snare on 2 and 4."""
    out = []
    for b in range(bars):
        t0 = start_tick + b * 4 * RES
        out += [hit(t0 + i * RES // 2, Pad.YELLOW, cymbal=True) for i in range(8)]
        out += [hit(t0, Pad.KICK), hit(t0 + 2 * RES, Pad.KICK), hit(t0 + RES, Pad.RED), hit(t0 + 3 * RES, Pad.RED)]
    return out


def blast(start_tick, bars):
    """Snare and kick on every 16th."""
    return [hit(start_tick + i * SIXTEENTH, p) for i in range(bars * 16) for p in (Pad.RED, Pad.KICK)]


class DensityTests(unittest.TestCase):
    def test_silence_between_sections_does_not_change_density(self):
        tight = features.compute(chart(groove(0, 8) + blast(8 * 4 * RES, 4)))
        gapped = features.compute(chart(groove(0, 8) + blast(40 * 4 * RES, 4)))
        for k in ('density_p50', 'density_p75', 'density_p90'):
            self.assertAlmostEqual(tight[k], gapped[k], places=6, msg=k)


class EnduranceTests(unittest.TestCase):
    def test_playing_the_chart_twice_does_not_raise_endurance(self):
        once = groove(0, 8) + blast(8 * 4 * RES, 8)
        twice = once + [hit(h.tick + 20 * 4 * RES, h.pad, h.cymbal) for h in once]
        a, b = features.compute(chart(once)), features.compute(chart(twice))
        for k in ('endurance_share_n8', 'endurance_longest_n8'):
            self.assertAlmostEqual(a[k], b[k], places=6, msg=k)

    def test_longer_unbroken_blast_scores_a_longer_stretch(self):
        short = features.compute(chart(groove(0, 4) + blast(4 * 4 * RES, 2)))
        long = features.compute(chart(groove(0, 4) + blast(4 * 4 * RES, 8)))
        self.assertGreater(long['endurance_longest_n8'], short['endurance_longest_n8'])

    def test_longest_stretch_breaks_at_gaps(self):
        dur = [1.0, 1.0, 1.0, 1.0]
        self.assertEqual(features.longest_stretch(dur, [True, True, False, True], [False, True, True, True]), 2.0)
        self.assertEqual(features.longest_stretch(dur, [True, True, True, True], [False, True, False, True]), 2.0)


if __name__ == '__main__':
    unittest.main()
