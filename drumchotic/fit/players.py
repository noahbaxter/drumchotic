"""Joint player-skill / chart-difficulty fit from leaderboard accuracy,
optionally with tournament finishes as extra evidence of player strength.

Misses on a chart are modelled as quasi-binomial with
    logit(p_miss) = mu + d_chart - s_player - g * log(1 + plays)
so evidence scales with how many misses the model expected: an FC on a
chart nobody misses on says almost nothing, a 97% on a chart where most
players miss hundreds of notes says a lot. g soaks up the edge a best
score gets from grinding a song. Scores far worse than the model expects
(a bad run, a lower difficulty) get downweighted.

The game floors percent, so 99% means up to 1% of notes missed. Counting the
full gap splits players more reliably than the bucket midpoint (split-half
agreement 0.909 vs 0.899): most scores sit at 97-100, where the midpoint
stretches the gaps between buckets. Reading misses from score points instead
measured no better; the noise is in who plays what, not in the rounding.

Tournament pairs add  T_WEIGHT * w * log sigmoid(beta * (s_winner - s_loser)).
"""
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize
from scipy.sparse import csr_matrix
from scipy.special import expit

from ..tuning import MIN_PERCENT, PRIOR, ROBUST, T_WEIGHT

ROUNDS = 4


def miss_count(percent, fc, notes):
    if fc:
        return 0.0
    if percent >= 100:
        return max(1.0, notes * 0.0025)
    return notes * (100 - percent) / 100


@dataclass
class Fit:
    difficulty: dict     # md5 -> d
    skill: dict          # user id (or match key for bracket-only players) -> s
    n_scores: dict       # md5 -> scores used
    mu: float
    grind: float
    beta: float
    phi: float


class _Problem:
    def __init__(self, X, G, k, n, nc, tw, tl, tweight):
        self.X, self.G, self.k, self.n, self.nc = X, G, k, n, nc
        self.tw, self.tl, self.tweight = tw, tl, tweight

    def unpack(self, z):
        return z[0], z[1], z[2], z[3:]       # mu, grind, beta, theta

    def __call__(self, z, w, phi):
        mu, g, beta, theta = self.unpack(z)
        eta = mu + g * self.G + self.X @ theta
        p = expit(eta)
        ll = w * (self.k * eta - self.n * np.logaddexp(0, eta))
        r = w * (self.n * p - self.k) / phi
        obj = -ll.sum() / phi + 0.5 * PRIOR * theta @ theta
        grad = np.concatenate([[r.sum(), r @ self.G, 0.0], self.X.T @ r + PRIOR * theta])
        if len(self.tw):
            s = theta[self.nc:]
            diff = s[self.tw] - s[self.tl]
            zt = beta * diff
            obj -= (self.tweight * -np.logaddexp(0, -zt)).sum()
            q = self.tweight * expit(-zt)        # d(-ll)/dz = -q
            grad[2] -= q @ diff
            gs = np.zeros(len(s))
            np.add.at(gs, self.tw, -q * beta)
            np.add.at(gs, self.tl, q * beta)
            grad[3 + self.nc:] += gs
        return obj, grad


def fit(songs, note_counts, matches=(), t_weight=T_WEIGHT):
    """songs: md5 -> leaderboard.Song; note_counts: md5 -> parsed expert note count;
    matches: (winner, loser, weight) with players as DMBot usernames or any other key."""
    charts, players, rows = {}, {}, []
    name_to_id = {}
    for md5, song in songs.items():
        n = note_counts.get(md5) or song.notes
        if not n:
            continue
        for s in song.scores:
            if s.percent < MIN_PERCENT:
                continue
            name_to_id[s.username] = s.user
            c = charts.setdefault(md5, len(charts))
            p = players.setdefault(s.user, len(players))
            rows.append((c, p, miss_count(s.percent, s.fc, n), n, np.log1p(s.play_count)))
    tw, tl, tweight = [], [], []
    for a, b, wt in matches:
        ia = players.setdefault(name_to_id.get(a, a), len(players))
        ib = players.setdefault(name_to_id.get(b, b), len(players))
        tw.append(ia); tl.append(ib); tweight.append(wt * t_weight)
    c_idx, p_idx, k, n, G = (np.array(v) for v in zip(*rows))
    c_idx, p_idx = c_idx.astype(int), p_idx.astype(int)
    obs, nc = len(k), len(charts)
    X = csr_matrix((np.concatenate([np.ones(obs), -np.ones(obs)]),
                    (np.tile(np.arange(obs), 2), np.concatenate([c_idx, nc + p_idx]))),
                   shape=(obs, nc + len(players)))
    prob = _Problem(X, -G, k, n, nc, np.array(tw, int), np.array(tl, int), np.array(tweight))
    mu0 = float(np.log(k.sum() / (n.sum() - k.sum())))
    z = np.concatenate([[mu0, 0.0, 1.0], np.zeros(X.shape[1])])
    w, phi = np.ones(obs), 1.0
    bounds = [(None, None), (None, None), (0.01, None)] + [(None, None)] * X.shape[1]
    for _ in range(ROUNDS):
        z = minimize(prob, z, args=(w, phi), jac=True, method='L-BFGS-B', bounds=bounds,
                     options={'maxiter': 3000}).x
        mu, g, beta, theta = prob.unpack(z)
        p = expit(mu + g * prob.G + X @ theta)
        pearson = (k - n * p) / np.sqrt(n * p * (1 - p))
        phi = float(np.sum(w * pearson ** 2) / max(obs - X.shape[1], 1))
        zz = np.abs(pearson) / np.sqrt(phi)
        w = np.where(zz <= ROBUST, 1.0, ROBUST / zz)
    counts = np.bincount(c_idx, minlength=nc)
    return Fit(
        difficulty={md5: theta[i] for md5, i in charts.items()},
        skill={u: theta[nc + i] for u, i in players.items()},
        n_scores={md5: int(counts[i]) for md5, i in charts.items()},
        mu=mu, grind=g, beta=beta, phi=phi,
    )
