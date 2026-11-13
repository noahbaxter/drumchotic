import unittest

import numpy as np

from drumchotic.fit.axes import AxisModel

AXES = {'speed': ['max_nps']}


def charts(length_effect, n=2000, seed=0):
    """Difficulty from speed alone, plus length_effect per log second past the median length."""
    rng = np.random.default_rng(seed)
    nps = rng.uniform(5, 30, n)
    length = np.exp(rng.uniform(np.log(60), np.log(1200), n))
    past = np.maximum(np.log(length) - np.median(np.log(length)), 0.0)
    y = np.log1p(nps) + length_effect * past + rng.normal(0, 0.05, n)
    return [{'max_nps': a, 'length_s': b, 'five_lane': 0.0} for a, b in zip(nps, length)], y


class FiveLaneStepTests(unittest.TestCase):
    def test_recovers_step(self):
        feats, y = charts(0.0)
        for i, f in enumerate(feats):
            f['five_lane'] = float(i % 10 == 0)
        y = y + 0.4 * np.array([f['five_lane'] for f in feats])
        m = AxisModel(power=1, axes=AXES).fit(feats, y)
        self.assertAlmostEqual(m.five_lane_step, 0.4, delta=0.03)

    def test_four_lane_only_leaves_it_off(self):
        feats, y = charts(0.0)
        self.assertEqual(AxisModel(power=1, axes=AXES).fit(feats, y).five_lane_step, 0.0)


class LengthDiscountTests(unittest.TestCase):
    def test_recovers_discount_on_long_charts(self):
        feats, y = charts(-0.3)
        m = AxisModel(power=1, axes=AXES).fit(feats, y)
        self.assertAlmostEqual(m.length_slope, -0.3, delta=0.03)

    def test_charts_at_or_under_typical_length_are_untouched(self):
        feats, y = charts(-0.3)
        m = AxisModel(power=1, axes=AXES).fit(feats, y)
        typical = float(np.exp(m.typical_log_length))
        term = m.length_term([{'max_nps': 10, 'length_s': s} for s in (30, typical, typical * 4)])
        self.assertEqual(term[0], 0.0)
        self.assertEqual(term[1], 0.0)
        self.assertLess(term[2], 0.0)

    def test_never_makes_long_charts_harder(self):
        feats, y = charts(+0.3)
        self.assertEqual(AxisModel(power=1, axes=AXES).fit(feats, y).length_slope, 0.0)

    def test_switched_off(self):
        feats, y = charts(-0.3)
        m = AxisModel(power=1, axes=AXES, length=False).fit(feats, y)
        self.assertEqual(m.length_slope, 0.0)
        self.assertTrue(np.all(m.length_term(feats) == 0.0))


if __name__ == '__main__':
    unittest.main()
