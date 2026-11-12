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

    def test_joke_tempo_cannot_make_one_note_dense(self):
        lone = DrumChart('test', TrackType.FOUR_LANE, True, RES, [Hit(RES * 100, 2000.0, Pad.KICK)],
                         tempos=[(0, 433433.433)])
        f = features.compute(lone)
        self.assertLess(f['density_p90'], 3)
        self.assertEqual(f['endurance_share_n8'], 0)

    def test_empty_drum_track_rates_as_nothing_to_play(self):
        f = features.compute(chart([]))
        self.assertEqual({k for k, v in f.items() if v}, {'length_s'})


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


class LinearTests(unittest.TestCase):
    def test_hihat_riding_on_the_kicks_does_not_break_linear(self):
        plain, layered = [], []
        step = SIXTEENTH // 2       # 62.5 ms, inside LINEAR_MS
        for i in range(32):
            pad = Pad.KICK if i % 2 == 0 else Pad.RED
            plain.append(hit(i * step, pad))
            layered.append(hit(i * step, pad))
            if i % 3 == 0:
                layered.append(hit(i * step, Pad.YELLOW, cymbal=True))
        a, b = features.compute(chart(plain)), features.compute(chart(layered))
        self.assertGreater(a['linear_w1'], 0)
        self.assertEqual(a['linear_w1'], b['linear_w1'])


def linear_16ths(order, bars):
    """16ths, one limb per note, cycling through order ('K' kick, 'S' snare)."""
    pads = {'K': Pad.KICK, 'S': Pad.RED}
    return [hit(i * SIXTEENTH, pads[order[i % len(order)]]) for i in range(bars * 16)]


class LimbTests(unittest.TestCase):
    def test_a_fill_is_a_hand_burst_but_not_hand_stamina(self):
        fill = [hit(4 * 4 * RES + i * SIXTEENTH // 2, Pad.RED) for i in range(8)]
        a, b = features.compute(chart(groove(0, 8))), features.compute(chart(groove(0, 8) + fill))
        self.assertGreater(b['run8_hands'], a['run8_hands'])
        self.assertAlmostEqual(b['run64_hands'], a['run64_hands'], delta=0.5)

    def test_offbeat_kicks_and_hands_together_raise_coordination(self):
        on = groove(0, 8)
        off = on + [hit(b * 4 * RES + RES * 3 // 4, p) for b in range(8) for p in (Pad.KICK, Pad.BLUE)]
        a, b = features.compute(chart(on)), features.compute(chart(off))
        self.assertEqual(a['coord_offbeat_w4'], 0)
        self.assertGreater(b['coord_offbeat_w4'], 0)


class LimbOrderTests(unittest.TestCase):
    def test_irregular_limb_order_is_more_novel_than_a_repeating_one(self):
        steady = features.compute(chart(linear_16ths('KSSS', 8)))
        irregular = features.compute(chart(linear_16ths('KSSKSKSSSKKSKSSSKSKKSSSKSSKSKSSS', 8)))
        self.assertGreater(irregular['limb_novel_w4'], steady['limb_novel_w4'])


if __name__ == '__main__':
    unittest.main()
