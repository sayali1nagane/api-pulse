"""Uptime ratio calculator for monitored endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from api_pulse.db import db_session
from api_pulse.repository import list_endpoints, get_recent_pings


@dataclass
class UptimeResult:
    url: str
    total_pings: int
    successful_pings: int
    uptime_pct: float  # 0.0 – 100.0
    window_hours: int

    def __str__(self) -> str:
        bar_width = 20
        filled = round(self.uptime_pct / 100 * bar_width)
        bar = "█" * filled + "░" * (bar_width - filled)
        return (
            f"{self.url}\n"
            f"  Window : last {self.window_hours}h\n"
            f"  Pings  : {self.successful_pings}/{self.total_pings}\n"
            f"  Uptime : {self.uptime_pct:6.2f}%  [{bar}]"
        )


def compute_uptime(
    url: str,
    conn,
    window_hours: int = 24,
) -> Optional[UptimeResult]:
    """Return uptime stats for a single endpoint URL."""
    limit = window_hours * 60  # generous upper bound (one ping/min)
    pings = get_recent_pings(conn, url, limit=limit)
    if not pings:
        return None

    # Filter to the requested time window
    import time
    cutoff = time.time() - window_hours * 3600
    pings = [p for p in pings if p.timestamp >= cutoff]
    if not pings:
        return None

    total = len(pings)
    successful = sum(1 for p in pings if p.success)
    pct = (successful / total) * 100.0
    return UptimeResult(
        url=url,
        total_pings=total,
        successful_pings=successful,
        uptime_pct=round(pct, 4),
        window_hours=window_hours,
    )


def compute_all_uptime(conn, window_hours: int = 24) -> list[UptimeResult]:
    """Return uptime stats for every registered endpoint."""
    results: list[UptimeResult] = []
    for endpoint in list_endpoints(conn):
        result = compute_uptime(endpoint.url, conn, window_hours=window_hours)
        if result is not None:
            results.append(result)
    return results
