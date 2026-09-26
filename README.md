# Vendor SLA Tracker

Tracks vendor SLA targets, records measurements, computes compliance, and detects breach streaks.

**Stack:** Python 3.12 · stdlib only · unittest

## Problem

SLAs define metric targets (e.g., uptime >= 99.9, p95 latency <= 200):
record() logs measurements; compliance() computes the share meeting
target over a trailing window; breach streaks find consecutive misses;
status() rolls up to ok/degraded/breached.

## Design decisions

- Each SLA has a metric name, a target, and a comparator: ">=" or "<=".
- Measurements are (at, value) pairs; compliance counts those within
- A breach streak is a run of consecutive misses: three missed
- status(): "breached" if any streak of 3+ misses is open at the end

## Layout

- `README.md`
- `src/sla_tracker.py`
- `tests/test_sla_tracker.py`
- `LICENSE`
- `.gitignore`

## Setup

No third-party dependencies — Python 3.11+ standard library only.

```bash
cd govops-sla-tracker
python -m unittest discover -s tests -v
```

## Usage

```python
from datetime import date
from src.sla_tracker import SLA, SLATracker

t = SLATracker()
t.add_sla(SLA("uptime", "monthly uptime %", 99.9))
t.record("uptime", date(2026, 6, 1), 99.95)
print(t.summary(date(2026, 6, 30)))
```

## License

MIT — see [LICENSE](LICENSE).
