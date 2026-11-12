"""Most-ergonomic hand assignment for a chart's hand notes (Viterbi).

State is where each hand sits on the kit, which hand hit last and how deep it
is into a run of same-hand strokes. A stroke costs more the faster its hand
moves, the further it travels, the deeper into a run it is, and when it
crosses the arms.
"""
from dataclasses import dataclass

import numpy as np

from .. import tuning
from ..chart.model import Pad

# rough kit layout from the drummer's seat, right-handed: x right, y away from you (kit units)
SURFACES = [
    ('snare', (0.0, 0.0)),
    ('tom1', (0.2, 0.8)),
    ('tom2', (1.0, 0.8)),
    ('floor', (1.2, -0.2)),
    ('hihat', (-1.0, 0.0)),
    ('ride', (1.8, 0.8)),
    ('crash', (2.2, 0.2)),
    ('lcrash', (-0.7, 0.9)),
]
N = len(SURFACES)
CYMBAL = np.array([False, False, False, False, True, True, True, True])
SNARE, HIHAT, LCRASH = 0, 4, 7
XYZ = np.column_stack([[xy for _, xy in SURFACES], CYMBAL * tuning.CYMBAL_HEIGHT])
DIST = np.linalg.norm(XYZ[:, None] - XYZ[None], axis=2)
LEFT, RIGHT, NONE = 0, 1, 2          # NONE: both hands hit last, no run going
WEAK = (tuning.LEFT_WEAKNESS, 1.0)
RUN = np.array(tuning.RUN_FACTOR)
K = len(RUN)                         # run positions tracked; the last covers every stroke past it
SHAPE = (N, N, 3, K)                 # [left position, right position, last hand, run position]
H = np.broadcast_to(np.arange(3)[None, None, :, None], SHAPE)
MIN_DT = 20.0
ALTERNATES = {HIHAT: (HIHAT, LCRASH)} if tuning.LEFT_CRASH else {}


def _crossing():
    """[left, right]: cost of the left hand sitting right of the right hand."""
    rx = XYZ[:, 0].copy()
    rx[HIHAT] = XYZ[SNARE, 0]
    over = np.maximum(0.0, XYZ[:, None, 0] - rx[None, :])
    cleared = np.where(CYMBAL[:, None] != CYMBAL[None, :], tuning.CROSS_CLEARED, 1.0)
    return tuning.CROSS_COST * over * cleared


CROSS = _crossing()
REACH = (tuning.REACH_COST * np.maximum(0.0, XYZ[:, 0] - tuning.LEFT_REACH_X), np.zeros(N))   # [hand][surface]


def surface(hit):
    if hit.pad == Pad.RED:
        return HIHAT if hit.cymbal else SNARE
    return {Pad.YELLOW: (1, 4), Pad.BLUE: (2, 5), Pad.GREEN: (3, 6)}[hit.pad][hit.cymbal]


def candidates(s):
    return ALTERNATES.get(s, (s,))


def speed_cost(dt_avg, run, weakness):
    """The run multiplier is full at HAND_SPEED_MS and faster, and fades out below it."""
    ratio = tuning.HAND_SPEED_MS / np.maximum(dt_avg, MIN_DT)
    run_mult = 1.0 + (RUN[run] - 1.0) * np.minimum(ratio, 1.0) ** tuning.RUN_FADE
    return weakness * ratio ** 3 * run_mult


def travel_cost(dist, dt):
    return dist * (0.05 + tuning.HAND_TRAVEL_MS / np.maximum(dt, MIN_DT))


def cross_cost(left, right, dt):
    return CROSS[left, right] * (1.0 + tuning.CROSS_MS / np.maximum(dt, MIN_DT))


@dataclass(frozen=True)
class Stroke:
    time_ms: float
    surface: int
    hand: int
    cost: float = 0.0
    run: int = 0                     # position in a same-hand run, 0 = first


# Single strokes are worked in the mover's frame: axis 0 the moving hand, axis 1 the other,
# last-hand index 0 = mover, 1 = other. RUN_NEXT is the run position the stroke lands on.
RUN_NEXT = np.zeros((3, K), int)
RUN_NEXT[0] = np.minimum(np.arange(K) + 1, K - 1)
SOURCES = [[i for i in range(3 * K) if RUN_NEXT.flat[i] == j] for j in range(K)]
FRAME_H = {LEFT: np.array([LEFT, RIGHT, NONE]), RIGHT: np.array([RIGHT, LEFT, NONE])}


def _frame(a, hand):
    return a if hand == LEFT else a.transpose(1, 0, 2, 3)[:, :, [1, 0, 2], :]


def _single(cost, times, t, c, hand, new, prev):
    tl, tl2, tr, tr2 = times
    mt, mt2 = (tl, tl2) if hand == LEFT else (tr, tr2)
    dt = t - _frame(mt, hand)
    cross_row = CROSS[c, :] if hand == LEFT else CROSS[:, c]
    tot = (_frame(cost, hand) + REACH[hand][c]
           + speed_cost((t - _frame(mt2, hand)) / 2, RUN_NEXT, WEAK[hand])
           + travel_cost(DIST[:, c][:, None, None, None], dt)
           + cross_row[None, :, None, None] * (1.0 + tuning.CROSS_MS / np.maximum(dt, MIN_DT)))
    arg_m = tot.argmin(0).reshape(N, 3 * K)
    best = tot.min(0).reshape(N, 3 * K)
    o = np.arange(N)
    cs = np.full(N, c)
    for j, src in enumerate(SOURCES):
        combo = np.array(src)[best[:, src].argmin(1)]
        m, hf, k = arg_m[o, combo], combo // K, combo % K
        if hand == LEFT:
            old = np.ravel_multi_index((m, o, FRAME_H[hand][hf], k), SHAPE)
            dest = np.ravel_multi_index((cs, o, np.full(N, LEFT), np.full(N, j)), SHAPE)
        else:
            old = np.ravel_multi_index((o, m, FRAME_H[hand][hf], k), SHAPE)
            dest = np.ravel_multi_index((o, cs, np.full(N, RIGHT), np.full(N, j)), SHAPE)
        val = best[o, combo]
        better = val < new.flat[dest]
        new.flat[dest[better]] = val[better]
        prev.flat[dest[better]] = old[better]


def _chord(cost, times, t, a, b, new, prev):
    tl, tl2, tr, tr2 = times
    dl, dr = t - tl, t - tr
    tot = (cost + REACH[LEFT][a]
           + speed_cost((t - tl2) / 2, 0, WEAK[LEFT]) + travel_cost(DIST[:, a][:, None, None, None], dl)
           + speed_cost((t - tr2) / 2, 0, WEAK[RIGHT]) + travel_cost(DIST[:, b][None, :, None, None], dr)
           + cross_cost(a, b, np.minimum(dl, dr)))
    i = int(tot.argmin())
    dest = np.ravel_multi_index((a, b, NONE, 0), SHAPE)
    if tot.flat[i] < new.flat[dest]:
        new.flat[dest] = tot.flat[i]
        prev.flat[dest] = i


def assign(onsets):
    """onsets: [(time_ms, sorted unique surfaces)] in time order.
    Returns (strokes, dropped) where dropped counts notes past two per onset."""
    cost = np.full(SHAPE, np.inf)
    cost[SNARE, HIHAT, NONE, 0] = 0.0
    times = [np.full(SHAPE, -1e9) for _ in range(4)]       # left last, left before, right last, right before
    hit_l, hit_r = (H == LEFT) | (H == NONE), (H == RIGHT) | (H == NONE)
    back, dropped, kept = [], 0, []
    for t, surfs in onsets:
        if len(surfs) > 2:
            dropped += len(surfs) - 2
            surfs = surfs[:2]
        kept.append((t, surfs))
        new = np.full(SHAPE, np.inf)
        prev = np.full(SHAPE, -1, dtype=np.int64)
        if len(surfs) == 1:
            for hand in (LEFT, RIGHT):
                for c in candidates(surfs[0]):
                    _single(cost, times, t, c, hand, new, prev)
        else:
            for sa, sb in ((surfs[0], surfs[1]), (surfs[1], surfs[0])):
                for a in candidates(sa):
                    for b in candidates(sb):
                        if a != b:
                            _chord(cost, times, t, a, b, new, prev)
        p = np.maximum(prev, 0)
        tl, tl2, tr, tr2 = (x.flat[p].reshape(SHAPE) for x in times)
        times = [np.where(hit_l, t, tl), np.where(hit_l, tl, tl2), np.where(hit_r, t, tr), np.where(hit_r, tr, tr2)]
        reached = prev >= 0
        step = np.zeros(SHAPE)
        step[reached] = new[reached] - cost.flat[p].reshape(SHAPE)[reached]
        back.append((prev, step))
        cost = new
    state = int(cost.argmin())
    path = []
    for prev, step in reversed(back):
        path.append((state, float(step.flat[state])))
        state = int(prev.flat[state])
    path.reverse()
    strokes = []
    for (t, surfs), (st, c) in zip(kept, path):
        l, r, h, k = (int(x) for x in np.unravel_index(st, SHAPE))
        if h == NONE:
            strokes += [Stroke(t, l, LEFT, c / 2), Stroke(t, r, RIGHT, c / 2)]
        else:
            strokes.append(Stroke(t, l if h == LEFT else r, h, c, k))
    return strokes, dropped


def cost_of(plan):
    """Total cost of a given sticking, plan: [(time_ms, {hand: surface})] with one or two hands.
    Same costs as assign, written out stroke by stroke, so tests can compare stickings."""
    pos = {LEFT: SNARE, RIGHT: HIHAT}
    last = {LEFT: (-1e9, -1e9), RIGHT: (-1e9, -1e9)}
    h, k, total = NONE, 0, 0.0
    for t, hands in plan:
        if len(hands) == 2:
            a, b = hands[LEFT], hands[RIGHT]
            dl, dr = t - last[LEFT][0], t - last[RIGHT][0]
            total += (REACH[LEFT][a] + speed_cost((t - last[LEFT][1]) / 2, 0, WEAK[LEFT])
                      + travel_cost(DIST[pos[LEFT], a], dl)
                      + speed_cost((t - last[RIGHT][1]) / 2, 0, WEAK[RIGHT]) + travel_cost(DIST[pos[RIGHT], b], dr)
                      + cross_cost(a, b, min(dl, dr)))
            h, k = NONE, 0
        else:
            (hand, c), = hands.items()
            k = min(k + 1, K - 1) if h == hand else 0
            h = hand
            dt = t - last[hand][0]
            left, right = (c, pos[RIGHT]) if hand == LEFT else (pos[LEFT], c)
            total += (REACH[hand][c] + speed_cost((t - last[hand][1]) / 2, k, WEAK[hand])
                      + travel_cost(DIST[pos[hand], c], dt)
                      + cross_cost(left, right, dt))
        for hand, c in hands.items():
            last[hand] = (t, last[hand][0])
            pos[hand] = c
    return float(total)
