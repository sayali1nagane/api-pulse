"""Latency trend reporting for monitored endpoints."""

from dataclasses import dataclass
from typing import List, Optional
from api_pulse.repository import get_recent_pings, list_endpoints
from api_pulse.models import PingResult


@dataclass
class EndpointStats:
    url: str
    name: str
    total_pings: int
    success_count: int
    failure_count: int
    avg_latency_ms: Optional[float]
    min_latency_ms: Optional[float]
    max_latency_ms: Optional[float]
    uptime_pct: float

    def __str__(self) -> str:
        latency = (
            f"avg={self.avg_latency_ms:.1f}ms  "
            f"min={self.min_latency_ms:.1f}ms  "
            f"max={self.max_latency_ms:.1f}ms"
            if self.avg_latency_ms is not None
            else "no latency data"
        )
        return (
            f"[{self.name}] {self.url}\n"
            f"  uptime={self.uptime_pct:.1f}%  "
            f"pings={self.total_pings}  "
            f"ok={self.success_count}  "
            f"fail={self.failure_count}\n"
            f"  latency: {latency}"
        )


def _compute_latency_stats(latencies: List[float]):
    """Return (avg, min, max) for a list of latency values, or (None, None, None) if empty."""
    if not latencies:
        return None, None, None
    return sum(latencies) / len(latencies), min(latencies), max(latencies)


def compute_stats(conn, url: str, name: str, limit: int = 50) -> EndpointStats:
    """Compute uptime and latency statistics for a single endpoint."""
    pings: List[PingResult] = get_recent_pings(conn, url, limit=limit)
    total = len(pings)
    if total == 0:
        return EndpointStats(
            url=url, name=name, total_pings=0,
            success_count=0, failure_count=0,
            avg_latency_ms=None, min_latency_ms=None, max_latency_ms=None,
            uptime_pct=0.0,
        )

    successes = [p for p in pings if p.success]
    latencies = [p.latency_ms for p in successes if p.latency_ms is not None]

    avg_lat, min_lat, max_lat = _compute_latency_stats(latencies)

    return EndpointStats(
        url=url,
        name=name,
        total_pings=total,
        success_count=len(successes),
        failure_count=total - len(successes),
        avg_latency_ms=avg_lat,
        min_latency_ms=min_lat,
        max_latency_ms=max_lat,
        uptime_pct=(len(successes) / total) * 100,
    )


def report_all(conn, limit: int = 50) -> List[EndpointStats]:
    """Return stats for every registered endpoint."""
    endpoints = list_endpoints(conn)
    return [compute_stats(conn, ep.url, ep.name, limit=limit) for ep in endpoints]
