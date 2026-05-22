"""Latency trend history: rolling statistics and sparkline rendering."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from api_pulse.repository import get_recent_pings


_SPARK_CHARS = " ▁▂▃▄▅▆▇█"


@dataclass
class LatencyHistory:
    url: str
    latencies: List[float]  # ms, oldest first; None entries replaced with -1
    window: int

    @property
    def available(self) -> int:
        return len([v for v in self.latencies if v >= 0])

    @property
    def average(self) -> Optional[float]:
        vals = [v for v in self.latencies if v >= 0]
        return sum(vals) / len(vals) if vals else None

    @property
    def minimum(self) -> Optional[float]:
        vals = [v for v in self.latencies if v >= 0]
        return min(vals) if vals else None

    @property
    def maximum(self) -> Optional[float]:
        vals = [v for v in self.latencies if v >= 0]
        return max(vals) if vals else None

    def sparkline(self) -> str:
        """Return a unicode sparkline for the latency series."""
        vals = [v for v in self.latencies if v >= 0]
        if not vals:
            return ""
        lo, hi = min(vals), max(vals)
        span = hi - lo or 1.0
        chars = []
        for v in self.latencies:
            if v < 0:
                chars.append("?")
            else:
                idx = int((v - lo) / span * (len(_SPARK_CHARS) - 1))
                chars.append(_SPARK_CHARS[idx])
        return "".join(chars)

    def __str__(self) -> str:
        avg = f"{self.average:.1f}" if self.average is not None else "n/a"
        lo = f"{self.minimum:.1f}" if self.minimum is not None else "n/a"
        hi = f"{self.maximum:.1f}" if self.maximum is not None else "n/a"
        spark = self.sparkline()
        return (
            f"{self.url}  [{spark}]  "
            f"avg={avg}ms  min={lo}ms  max={hi}ms  "
            f"samples={self.available}/{self.window}"
        )


def fetch_history(conn, url: str, window: int = 20) -> LatencyHistory:
    """Load the last *window* pings for *url* and build a LatencyHistory."""
    pings = get_recent_pings(conn, url, limit=window)
    # pings are newest-first from repository; reverse for chronological order
    pings = list(reversed(pings))
    latencies = [p.latency_ms if p.latency_ms is not None else -1.0 for p in pings]
    return LatencyHistory(url=url, latencies=latencies, window=window)
