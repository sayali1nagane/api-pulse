"""Latency trend analysis: slope-based direction and simple moving average."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from api_pulse.repository import get_recent_pings


@dataclass
class TrendResult:
    url: str
    sample_count: int
    moving_avg_ms: Optional[float]  # average of the last window
    slope_ms_per_ping: Optional[float]  # linear regression slope
    direction: str  # 'improving', 'degrading', 'stable', or 'insufficient_data'

    def __str__(self) -> str:
        if self.direction == "insufficient_data":
            return f"{self.url}: insufficient data ({self.sample_count} pings)"
        arrow = {"improving": "↓", "degrading": "↑", "stable": "→"}.get(self.direction, "?")
        return (
            f"{self.url}: {arrow} {self.direction}  "
            f"avg={self.moving_avg_ms:.1f}ms  "
            f"slope={self.slope_ms_per_ping:+.2f}ms/ping  "
            f"(n={self.sample_count})"
        )


def _linear_slope(values: List[float]) -> float:
    """Return the slope of the best-fit line through (index, value) pairs."""
    n = len(values)
    x_mean = (n - 1) / 2.0
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def analyze_trend(
    conn,
    url: str,
    limit: int = 20,
    stable_threshold_ms: float = 5.0,
) -> TrendResult:
    """Compute latency trend for a single endpoint URL."""
    pings = get_recent_pings(conn, url, limit=limit)
    successful = [p for p in pings if p.success and p.latency_ms is not None]

    if len(successful) < 3:
        return TrendResult(
            url=url,
            sample_count=len(successful),
            moving_avg_ms=None,
            slope_ms_per_ping=None,
            direction="insufficient_data",
        )

    latencies: List[float] = [p.latency_ms for p in successful]
    moving_avg = sum(latencies) / len(latencies)
    slope = _linear_slope(latencies)

    if abs(slope) <= stable_threshold_ms:
        direction = "stable"
    elif slope > 0:
        direction = "degrading"
    else:
        direction = "improving"

    return TrendResult(
        url=url,
        sample_count=len(successful),
        moving_avg_ms=moving_avg,
        slope_ms_per_ping=slope,
        direction=direction,
    )


def analyze_all(
    conn,
    endpoints,
    limit: int = 20,
    stable_threshold_ms: float = 5.0,
) -> List[TrendResult]:
    """Compute trend results for every endpoint."""
    return [
        analyze_trend(conn, ep.url, limit=limit, stable_threshold_ms=stable_threshold_ms)
        for ep in endpoints
    ]
