
"""Vendor SLA tracker.

SLAs define metric targets (e.g., uptime >= 99.9, p95 latency <= 200):
record() logs measurements; compliance() computes the share meeting
target over a trailing window; breach streaks find consecutive misses;
status() rolls up to ok/degraded/breached.

Design:
- Each SLA has a metric name, a target, and a comparator: ">=" or "<=".
- Measurements are (at, value) pairs; compliance counts those within
  the window that meet the target.
- A breach streak is a run of consecutive misses: three missed
  uptime checks in a row is one incident, not three.
- status(): "breached" if any streak of 3+ misses is open at the end
  of the window, "degraded" if compliance < 1.0, else "ok".
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass
class SLA:
    """One service-level target."""
    sla_id: str
    metric: str
    target: float
    comparator: str = ">="

    def meets(self, value):
        if self.comparator == ">=":
            return value >= self.target
        if self.comparator == "<=":
            return value <= self.target
        raise ValueError("bad comparator %r" % (self.comparator,))


@dataclass
class Measurement:
    at: date
    value: float


class SLATracker:
    """SLA definitions plus measurement history."""

    def __init__(self, window_days=30):
        if window_days <= 0:
            raise ValueError("window_days must be positive")
        self.window_days = window_days
        self._slas = {}
        self._measurements = {}

    def add_sla(self, sla):
        if sla.sla_id in self._slas:
            raise ValueError("duplicate sla_id %r" % (sla.sla_id,))
        sla.meets(sla.target)  # validate comparator eagerly
        self._slas[sla.sla_id] = sla
        self._measurements[sla.sla_id] = []
        return sla

    def _require(self, sla_id):
        try:
            return self._slas[sla_id]
        except KeyError:
            raise KeyError("unknown sla_id %r" % (sla_id,))

    def record(self, sla_id, at, value):
        sla = self._require(sla_id)
        if not isinstance(at, date):
            raise TypeError("at must be a datetime.date")
        if not isinstance(value, (int, float)):
            raise TypeError("value must be numeric")
        measurement = Measurement(at, float(value))
        self._measurements[sla_id].append(measurement)
        self._measurements[sla_id].sort(key=lambda m: m.at)
        return measurement

    def _window(self, sla_id, as_of):
        start = as_of - timedelta(days=self.window_days)
        return [m for m in self._measurements[sla_id]
                if start <= m.at <= as_of]

    def compliance(self, sla_id, as_of):
        """Share of in-window measurements meeting the target."""
        sla = self._require(sla_id)
        measurements = self._window(sla_id, as_of)
        if not measurements:
            return 1.0
        hit = sum(1 for m in measurements if sla.meets(m.value))
        return round(hit / len(measurements), 3)

    def misses(self, sla_id, as_of):
        sla = self._require(sla_id)
        return [m for m in self._window(sla_id, as_of)
                if not sla.meets(m.value)]

    def breach_streaks(self, sla_id, as_of):
        """Consecutive-miss runs as lists of measurements."""
        sla = self._require(sla_id)
        streaks, current = [], []
        for measurement in self._window(sla_id, as_of):
            if sla.meets(measurement.value):
                if current:
                    streaks.append(current)
                    current = []
            else:
                current.append(measurement)
        if current:
            streaks.append(current)
        return streaks

    def longest_streak(self, sla_id, as_of):
        streaks = self.breach_streaks(sla_id, as_of)
        return max((len(s) for s in streaks), default=0)

    def status(self, sla_id, as_of):
        sla = self._require(sla_id)
        measurements = self._window(sla_id, as_of)
        if not measurements:
            return "ok"
        if self.longest_streak(sla_id, as_of) >= 3:
            return "breached"
        if self.compliance(sla_id, as_of) < 1.0:
            return "degraded"
        return "ok"

    def summary(self, as_of):
        return {sla_id: {
            "metric": sla.metric,
            "compliance": self.compliance(sla_id, as_of),
            "longest_streak": self.longest_streak(sla_id, as_of),
            "status": self.status(sla_id, as_of),
        } for sla_id, sla in sorted(self._slas.items())}
