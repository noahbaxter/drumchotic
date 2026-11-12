import unittest

from drumchotic.measure import sticking as s
from drumchotic.measure.sticking import CROSS, HIHAT, LCRASH, LEFT, RIGHT, SNARE

TOM1, TOM2, FLOOR, RIDE = 1, 2, 3, 5
SIXTEENTHS_120 = 125.0      # ms between 16ths at 120 BPM
BLAST = 62.5                # 16ths at 240 BPM


def stream(gap, pattern, n=32, surface=SNARE):
    """n single strokes gap ms apart, hands cycling through a pattern like 'RRLL'."""
    return [(i * gap, {LEFT if pattern[i % len(pattern)] == 'L' else RIGHT: surface}) for i in range(n)]


def per_stroke(gap, pattern, n=32):
    return s.cost_of(stream(gap, pattern, n)) / n


def as_plan(strokes):
    plan = {}
    for st in strokes:
        plan.setdefault(st.time_ms, {})[st.hand] = st.surface
    return sorted(plan.items())


class CrossingTests(unittest.TestCase):
    def test_right_hand_on_hihat_is_the_normal_grip(self):
        self.assertEqual(CROSS[SNARE, HIHAT], 0.0)

    def test_uncrossed_costs_nothing(self):
        self.assertEqual(CROSS[SNARE, TOM2], 0.0)

    def test_crossings_rank_like_a_drummer_says(self):
        self.assertLess(CROSS[TOM1, SNARE], CROSS[TOM2, TOM1])
        self.assertLess(CROSS[TOM2, TOM1], CROSS[TOM2, SNARE])
        self.assertLess(CROSS[TOM2, SNARE], CROSS[FLOOR, SNARE])

    def test_fast_crossing_costs_more_than_slow(self):
        self.assertGreater(s.cross_cost(TOM2, SNARE, 60.0), s.cross_cost(TOM2, SNARE, 500.0))

    def test_tom_fill_crosses_no_worse_than_tom1_over_snare(self):
        fill = [SNARE, TOM1, TOM2, FLOOR] * 4
        strokes, _ = s.assign([(i * SIXTEENTHS_120, [x]) for i, x in enumerate(fill)])
        pos = {LEFT: SNARE, RIGHT: HIHAT}
        for st in strokes:
            pos[st.hand] = st.surface
            self.assertLessEqual(CROSS[pos[LEFT], pos[RIGHT]], CROSS[TOM1, SNARE], st)


class RunTests(unittest.TestCase):
    def test_doubles_cost_about_the_same_as_alternating(self):
        self.assertLess(per_stroke(BLAST, 'RRLL'), 1.5 * per_stroke(BLAST, 'RL'))

    def test_three_in_a_row_is_much_worse_than_doubles(self):
        self.assertGreater(per_stroke(BLAST, 'RRRL'), 2 * per_stroke(BLAST, 'RRLL'))

    def test_four_in_a_row_is_worse_than_three(self):
        self.assertGreater(per_stroke(BLAST, 'RRRRLLLL'), per_stroke(BLAST, 'RRRL'))

    def test_slow_one_hand_stream_stays_cheap(self):
        self.assertLess(per_stroke(500.0, 'R'), 0.2)


class AssignTests(unittest.TestCase):
    onsets = [(i * 90.0, [x]) for i, x in enumerate([SNARE, HIHAT, SNARE, TOM1, TOM2, FLOOR, SNARE, RIDE] * 3)] \
        + [(2200.0, [SNARE, RIDE]), (2300.0, [HIHAT]), (2350.0, [SNARE]), (2400.0, [TOM2, HIHAT])]

    def test_stroke_costs_add_up_to_the_same_total_as_cost_of(self):
        strokes, _ = s.assign(self.onsets)
        self.assertAlmostEqual(sum(st.cost for st in strokes), s.cost_of(as_plan(strokes)), places=6)

    def test_assigned_sticking_beats_plain_alternating(self):
        strokes, _ = s.assign(self.onsets)
        alt = [(t, {RIGHT if i % 2 == 0 else LEFT: x[0]} if len(x) == 1 else {LEFT: min(x), RIGHT: max(x)})
               for i, (t, x) in enumerate(self.onsets)]
        self.assertLessEqual(s.cost_of(as_plan(strokes)), s.cost_of(alt) + 1e-9)

    def test_ride_over_a_kick_stream_stays_in_the_right_hand(self):
        strokes, _ = s.assign([(i * 182.0, [RIDE]) for i in range(16)])
        self.assertEqual({st.hand for st in strokes}, {RIGHT})

    def test_left_hand_up_on_the_toms_takes_the_left_crash(self):
        strokes, _ = s.assign([(0.0, [TOM1, TOM2]), (60.0, [TOM2, HIHAT])])
        self.assertIn((LEFT, LCRASH), [(st.hand, st.surface) for st in strokes if st.time_ms == 60.0])


if __name__ == '__main__':
    unittest.main()
