import unittest

import numpy as np

from drumchotic.chart.model import Pad
from drumchotic.measure import rarity
from tests.test_features import RES, SIXTEENTH, chart, groove, hit


def odd_fill(bars):
    """Kick and toms in a 5-note figure across 16ths: no other artist plays it."""
    pads = (Pad.KICK, Pad.BLUE, Pad.KICK, Pad.GREEN, Pad.RED)
    return [hit(i * SIXTEENTH * 3 // 2, pads[i % 5]) for i in range(bars * 10)]


def table(by_artist):
    return rarity.Table.build({a: [rarity.runs(c)[1] for c in cs] for a, cs in by_artist.items()})


class RarityTests(unittest.TestCase):
    def test_common_groove_is_familiar_and_odd_fill_is_rare(self):
        lib = table({f'artist{i}': [chart(groove(0, 4))] for i in range(10)} | {'odd': [chart(odd_fill(4))]})
        common = rarity.features(*rarity.runs(chart(groove(0, 4))), lib, in_table=False)
        rare = rarity.features(*rarity.runs(chart(odd_fill(4))), lib, in_table=True)
        self.assertLess(common['rarity_mean'], 0.1)
        self.assertAlmostEqual(rare['rarity_mean'], np.log(11))

    def test_own_artist_does_not_make_a_chart_familiar(self):
        own = chart(odd_fill(4))
        lib = table({'odd': [own, chart(odd_fill(8))], **{f'artist{i}': [chart(groove(0, 4))] for i in range(4)}})
        self.assertAlmostEqual(rarity.features(*rarity.runs(own), lib, in_table=True)['rarity_mean'],
                               np.log(5))

    def test_run_not_in_table_counts_as_rarest(self):
        lib = table({'a': [chart(groove(0, 4))], 'b': [chart(groove(0, 4))]})
        f = rarity.features(*rarity.runs(chart(odd_fill(4))), lib, in_table=False)
        self.assertAlmostEqual(f['rarity_mean'], np.log(2))

    def test_too_few_onsets_scores_zero(self):
        lib = table({'a': [chart(groove(0, 4))]})
        self.assertEqual(rarity.features(*rarity.runs(chart(groove(0, 1)[:3])), lib, in_table=False),
                         rarity.EMPTY)

    def test_shifting_off_the_beat_is_a_different_pattern(self):
        _, on = rarity.runs(chart(groove(0, 2)))
        _, off = rarity.runs(chart(groove(RES // 4, 2)))
        self.assertFalse(set(on) & set(off))


if __name__ == '__main__':
    unittest.main()
