"""Rate helpers over event times (ms, sorted)."""
import numpy as np

from ..tuning import MIN_GAP_MS


def fastest_run_at(times, n):
    """(notes/s, start ms, end ms) of the fastest run of n consecutive events."""
    if len(times) < n:
        return 0.0, 0.0, 0.0
    span = times[n - 1:] - times[:len(times) - n + 1]
    i = int(np.argmin(span))
    return float((n - 1) / max(span[i], (n - 1) * MIN_GAP_MS) * 1000.0), float(times[i]), float(times[i + n - 1])


def fastest_run(times, n):
    """Highest rate (notes/s) sustained over any n consecutive events."""
    return fastest_run_at(times, n)[0]


def window_sums(times, weights, window_s):
    """Summed weights per second over each window [t, t+W) starting at an event."""
    w = window_s * 1000.0
    cs = np.concatenate([[0.0], np.cumsum(weights)])
    end = np.searchsorted(times, times + w, side='left')
    return (cs[end] - cs[np.arange(len(times))]) / window_s


def window_sums_at(starts, times, weights, window_s):
    """Summed weights per second of events (times, weights) in each window [s, s+W) for s in starts."""
    cs = np.concatenate([[0.0], np.cumsum(weights)])
    lo = np.searchsorted(times, starts, side='left')
    hi = np.searchsorted(times, starts + window_s * 1000.0, side='left')
    return (cs[hi] - cs[lo]) / window_s


def worst_window(times, weights, window_s):
    if len(times) == 0:
        return 0.0
    return float(window_sums(times, weights, window_s).max())
