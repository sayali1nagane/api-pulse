"""Daily/periodic summary report generation for monitored endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from api_pulse.db import db_session
from api_pulse.repository import list_endpoints, get_recent_pings
from api_pulse.reporter import compute_stats


@dataclass
class SummaryEntry:
    url: str
    period_hours: int
    total_pings: int
    success_count: int
    failure_count: int
    avg_latency_ms: Optional[float]
    uptime_pct: float

    def __str__(self) -> str:
        latency = f"{self.avg_latency_ms:.1f}ms" if self.avg_latency_ms is not None else "N/A"
        return (
            f"[{self.url}] "
            f"period={self.period_hours}h "
            f"pings={self.total_pings} "
            f"up={self.uptime_pct:.1f}% "
            f"avg_latency={latency}"
        )


def summarize_endpoint(conn, url: str, period_hours: int = 24) -> Optional[SummaryEntry]:
    """Return a SummaryEntry for *url* covering the last *period_hours* hours."""
    limit = period_hours * 120  # generous upper bound (pings every 30s)
    pings = get_recent_pings(conn, url, limit=limit)
    if not pings:
        return None

    cutoff = datetime.utcnow() - timedelta(hours=period_hours)
    recent = [p for p in pings if p.timestamp >= cutoff]
    if not recent:
        return None

    success = [p for p in recent if p.success]
    latencies = [p.latency_ms for p in success if p.latency_ms is not None]
    avg_latency = sum(latencies) / len(latencies) if latencies else None
    uptime = len(success) / len(recent) * 100.0

    return SummaryEntry(
        url=url,
        period_hours=period_hours,
        total_pings=len(recent),
        success_count=len(success),
        failure_count=len(recent) - len(success),
        avg_latency_ms=avg_latency,
        uptime_pct=uptime,
    )


def summarize_all(conn, period_hours: int = 24) -> List[SummaryEntry]:
    """Return summary entries for every registered endpoint."""
    results = []
    for endpoint in list_endpoints(conn):
        entry = summarize_endpoint(conn, endpoint.url, period_hours=period_hours)
        if entry is not None:
            results.append(entry)
    return results
