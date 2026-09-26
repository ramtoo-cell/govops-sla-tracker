
"""Tests for the vendor SLA tracker."""
import unittest
from datetime import date

from src.sla_tracker import SLA, SLATracker

AS_OF = date(2026, 6, 30)


def _tracker():
    t = SLATracker(window_days=30)
    t.add_sla(SLA("uptime", "monthly uptime %", 99.9, ">="))
    t.add_sla(SLA("latency", "p95 latency ms", 200.0, "<="))
    for day, value in [(1, 99.95), (2, 99.7), (3, 99.5), (4, 99.2),
                       (5, 99.95), (10, 150.0), (11, 250.0)]:
        sla = "uptime" if day <= 5 else "latency"
        t.record(sla, date(2026, 6, day), value)
    return t


class TestSLATracker(unittest.TestCase):
    def test_compliance(self):
        t = _tracker()
        self.assertEqual(t.compliance("uptime", AS_OF), 0.4)
        self.assertEqual(t.compliance("latency", AS_OF), 0.5)

    def test_misses(self):
        t = _tracker()
        self.assertEqual(len(t.misses("uptime", AS_OF)), 3)

    def test_breach_streaks(self):
        t = _tracker()
        streaks = t.breach_streaks("uptime", AS_OF)
        self.assertEqual(len(streaks), 1)
        self.assertEqual(len(streaks[0]), 3)

    def test_longest_streak(self):
        self.assertEqual(_tracker().longest_streak("uptime", AS_OF), 3)
        self.assertEqual(_tracker().longest_streak("latency", AS_OF), 1)

    def test_status_breached(self):
        self.assertEqual(_tracker().status("uptime", AS_OF), "breached")

    def test_status_degraded(self):
        self.assertEqual(_tracker().status("latency", AS_OF), "degraded")

    def test_status_ok(self):
        t = SLATracker()
        t.add_sla(SLA("s", "m", 99.0))
        t.record("s", date(2026, 6, 1), 99.5)
        self.assertEqual(t.status("s", AS_OF), "ok")

    def test_old_measurements_age_out(self):
        t = SLATracker(window_days=30)
        t.add_sla(SLA("s", "m", 99.0))
        t.record("s", date(2026, 1, 1), 10.0)
        self.assertEqual(t.compliance("s", AS_OF), 1.0)
        self.assertEqual(t.status("s", AS_OF), "ok")

    def test_duplicate_sla_raises(self):
        t = SLATracker()
        t.add_sla(SLA("s", "m", 1.0))
        with self.assertRaises(ValueError):
            t.add_sla(SLA("s", "m", 2.0))

    def test_unknown_sla_raises(self):
        with self.assertRaises(KeyError):
            _tracker().compliance("zzz", AS_OF)


if __name__ == "__main__":
    unittest.main()
