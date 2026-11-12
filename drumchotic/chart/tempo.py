import bisect

DEFAULT_US_PER_QN = 500_000  # 120 BPM


class TempoMap:
    def __init__(self, tempos_us, resolution):
        """tempos_us: (tick, microseconds per quarter note) pairs, any order."""
        tempos = sorted(dict(tempos_us).items())
        if not tempos or tempos[0][0] != 0:
            tempos.insert(0, (0, DEFAULT_US_PER_QN))
        self.resolution = resolution
        self._ticks = [t for t, _ in tempos]
        self._us = [us for _, us in tempos]
        self._ms = [0.0]
        for i in range(1, len(tempos)):
            self._ms.append(self._ms[-1] + self._span_ms(self._ticks[i] - self._ticks[i - 1], self._us[i - 1]))

    def _span_ms(self, ticks, us):
        return ticks * us / self.resolution / 1000.0

    def ms(self, tick):
        i = bisect.bisect_right(self._ticks, tick) - 1
        return self._ms[i] + self._span_ms(tick - self._ticks[i], self._us[i])

    def bpms(self):
        return [(t, 60_000_000 / us) for t, us in zip(self._ticks, self._us)]
