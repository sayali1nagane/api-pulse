"""Compare ping statistics between two time windows for a given endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from api_pulse.db import db_session
from api_pulse.repository import get_recent_pings


@dataclass
class WindowStats:
    count: int
    success_rate: float  # 0.0 – 1.0
    avg_latency_ms: Optional[float]


@dataclass
class ComparisonResult:
    url: str
    window_a: WindowStats
    window_b: WindowStats

    @property
    def latency_delta_ms(self) -> Optional[float]:
        """Positive means window_b is slower than window_a."""
        if self.window_a.avg_latency_ms is None or self.window_b.avg_latency_ms is None:
            return None
        return self.window_b.avg_latency_ms - self.window_a.avg_latency_ms

    @property
    def success_rate_delta(self) -> float:
        """Positive means window_b has a higher success rate."""
        return self.window_b.success_rate - self.window_a.success_rate

    def __str__(self) -> str:
        lat = (
            f"{self.latency_delta_ms:+.1f} ms"
            if self.latency_delta_ms is not None
            else "n/a"
        )
        sr = f"{self.success_rate_delta:+.1%}"
        return (
            f"{self.url}  latency_delta={lat}  "
            f"success_rate_delta={sr}  "
            f"(a_n={self.window_a.count}, b_n={self.window_b.count})"
        )


def _stats_from_pings(pings) -> WindowStats:
    if not pings:
        return WindowStats(count=0, success_rate=0.0, avg_latency_ms=None)
    successes = [p for p in pings if p.success]
    latencies = [p.latency_ms for p in successes if p.latency_ms is not None]
    avg = sum(latencies) / len(latencies) if latencies else None
    return WindowStats(
        count=len(pings),
        success_rate=len(successes) / len(pings),
        avg_latency_ms=avg,
    )


def compare_endpoint(
    url: str,
    window_a_n: int = 20,
    window_b_n: int = 20,
    conn=None,
) -> ComparisonResult:
    """Compare the most-recent *window_b_n* pings against the prior *window_a_n* pings."""
    with db_session(conn) as c:
        # Fetch enough pings to cover both windows
        total = window_a_n + window_b_n
        all_pings = get_recent_pings(url, limit=total, conn=c)

    # all_pings is ordered newest-first
    window_b = all_pings[:window_b_n]
    window_a = all_pings[window_b_n : window_b_n + window_a_n]

    return ComparisonResult(
        url=url,
        window_a=_stats_from_pings(window_a),
        window_b=_stats_from_pings(window_b),
    )
