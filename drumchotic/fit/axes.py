"""Difficulty from per-axis scores that only ever go up.

Every feature becomes log(1 + value) plus hinge terms above a few of its
quantiles, and all weights are held non-negative, so each axis is a
convex, increasing function of its features. That keeps the sub-scores
readable and lets them extrapolate past the hardest charts with scores.

Axes combine as a power mean,  d = b + (sum_a axis_a ** p) ** (1 / p):
p = 1 adds them up, larger p lets the hardest axis dominate.
On top of that, an optional length discount: d += slope * max(log(length / typical length), 0),
and a step for 5-lane tracks: d += step * five_lane.
"""
import numpy as np
from scipy.optimize import lsq_linear, minimize

from ..tuning import AXES, AXIS_POWER, AXIS_SCALE, FIVE_LANE_STEP, KNOTS, LENGTH_DISCOUNT, RIDGE


class AxisModel:
    def __init__(self, power=AXIS_POWER, axes=None, length=LENGTH_DISCOUNT, five_lane=FIVE_LANE_STEP):
        """axes: {axis: [features]} to fit, default every axis in tuning.AXES.
        length: fit the length discount, as tuning.LENGTH_DISCOUNT.
        five_lane: fit the 5-lane step, as tuning.FIVE_LANE_STEP."""
        self.power = power
        self.axes = AXES if axes is None else axes
        self.length = length
        self.five_lane = five_lane
        self.length_slope, self.typical_log_length = 0.0, 0.0
        self.five_lane_step = 0.0

    def fit(self, feats, y, weights=None):
        """feats: list of feature dicts; y: target difficulty."""
        logs = {k: np.log1p(np.array([f[k] for f in feats])) for ax in self.axes.values() for k in ax}
        self.base = {k: float(np.quantile(v, 0.05)) for k, v in logs.items()}
        self.knots = {k: [float(np.quantile(v, q)) for q in KNOTS] for k, v in logs.items()}
        B, self.cols = self._basis(feats)
        self.col_axis = np.array([list(self.axes).index(c[0]) for c in self.cols])
        y = np.asarray(y, float)
        w2 = np.ones(len(y)) if weights is None else np.asarray(weights, float)
        lam = RIDGE * len(y)
        # plain sum first: a linear problem, and a good start for the power mean
        A = np.column_stack([np.ones(len(y)), B]) * np.sqrt(w2)[:, None]
        sol = lsq_linear(np.vstack([A, np.sqrt(lam) * np.eye(A.shape[1])[1:]]),
                         np.r_[y * np.sqrt(w2), np.zeros(B.shape[1])],
                         bounds=(np.r_[-np.inf, np.zeros(B.shape[1])], np.inf))
        z = sol.x
        if self.power != 1:
            p = self.power
            n_ax = len(self.axes)

            def f(z):
                b, c = z[0], z[1:]
                ax = np.zeros((len(y), n_ax))
                np.add.at(ax.T, self.col_axis, (B * c).T)
                S = (ax ** p).sum(1) ** (1 / p)
                r = w2 * (b + S - y)
                dS = np.where(S[:, None] > 0, (ax / np.maximum(S, 1e-12)[:, None]) ** (p - 1), 0.0)
                gc = (B * dS[:, self.col_axis]).T @ r + lam * c
                return 0.5 * (w2 * (b + S - y) ** 2).sum() + 0.5 * lam * c @ c, np.r_[r.sum(), gc]

            z = minimize(f, z, jac=True, method='L-BFGS-B',
                         bounds=[(None, None)] + [(0, None)] * B.shape[1]).x
        self.intercept, self.coef = float(z[0]), z[1:]
        if self.length:
            self._fit_length(feats, y, w2)
        if self.five_lane:
            self._fit_five_lane(feats, y, w2)
        return self

    def _fit_five_lane(self, feats, y, w):
        """How much more 5-lane charts miss than the rest, after the axes and length."""
        on = self._five_lane_x(feats) > 0
        if not on.any() or on.all():
            return
        r = y - self.predict(feats)
        rest = np.average(r[~on], weights=w[~on])
        self.five_lane_step = float(np.average(r[on], weights=w[on]) - rest)
        self.intercept += rest

    def _five_lane_x(self, feats):
        return np.array([f['five_lane'] for f in feats], float)

    def five_lane_term(self, feats):
        """What being a 5-lane track adds to each chart's difficulty."""
        return self.five_lane_step * self._five_lane_x(feats)

    def _fit_length(self, feats, y, w):
        """Weighted least squares of what the axes leave over on the length term, slope held <= 0."""
        logs = np.log([f['length_s'] for f in feats])
        self.typical_log_length = float(np.median(logs))
        x = self._length_x(feats)
        r = y - self.predict(feats)
        xm, rm = np.average(x, weights=w), np.average(r, weights=w)
        slope = np.average((x - xm) * (r - rm), weights=w) / max(np.average((x - xm) ** 2, weights=w), 1e-12)
        self.length_slope = min(float(slope), 0.0)
        self.intercept += rm - self.length_slope * xm

    def _length_x(self, feats):
        return np.maximum(np.log([f['length_s'] for f in feats]) - self.typical_log_length, 0.0)

    def length_term(self, feats):
        """What length adds to each chart's difficulty (<= 0 for charts longer than typical)."""
        return self.length_slope * self._length_x(feats)

    def _basis(self, feats):
        cols, out = [], []
        for ax, keys in self.axes.items():
            for k in keys:
                x = np.log1p(np.array([f[k] for f in feats]))
                out.append(np.maximum(x - self.base[k], 0.0)); cols.append((ax, k, 'log'))
                for q, t in zip(KNOTS, self.knots[k]):
                    out.append(np.maximum(x - t, 0.0)); cols.append((ax, k, f'>q{int(q * 100)}'))
        return np.column_stack(out), cols

    def axis_scores(self, feats):
        """Per-axis score for each chart, after AXIS_SCALE: {axis: array}."""
        B, _ = self._basis(feats)
        parts = B * self.coef
        return {ax: AXIS_SCALE.get(ax, 1.0) * parts[:, self.col_axis == i].sum(1)
                for i, ax in enumerate(self.axes)}

    def predict(self, feats):
        ax = np.column_stack(list(self.axis_scores(feats).values()))
        return (self.intercept + (ax ** self.power).sum(1) ** (1 / self.power) + self.length_term(feats)
                + self.five_lane_term(feats))
