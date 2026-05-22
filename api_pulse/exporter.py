"""Export ping history and stats to CSV format."""

import csv
import io
from datetime import datetime
from typing import List, Optional

from api_pulse.models import Endpoint, PingResult
from api_pulse.repository import list_endpoints, get_recent_pings
from api_pulse.reporter import compute_stats


def export_pings_csv(conn, url: Optional[str] = None, limit: int = 500) -> str:
    """Export raw ping results to CSV string.

    Args:
        conn: SQLite connection.
        url: If provided, export only pings for this endpoint URL.
        limit: Maximum number of ping rows per endpoint.

    Returns:
        CSV-formatted string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["url", "checked_at", "status_code", "latency_ms", "error"])

    endpoints: List[Endpoint] = list_endpoints(conn)
    if url:
        endpoints = [e for e in endpoints if e.url == url]

    for endpoint in endpoints:
        pings: List[PingResult] = get_recent_pings(conn, endpoint.id, limit=limit)
        for ping in pings:
            writer.writerow([
                endpoint.url,
                ping.checked_at,
                ping.status_code if ping.status_code is not None else "",
                f"{ping.latency_ms:.2f}" if ping.latency_ms is not None else "",
                ping.error or "",
            ])

    return output.getvalue()


def export_stats_csv(conn) -> str:
    """Export aggregated stats for all endpoints to CSV string.

    Args:
        conn: SQLite connection.

    Returns:
        CSV-formatted string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "url", "total_pings", "success_count", "failure_count",
        "uptime_pct", "avg_latency_ms", "min_latency_ms", "max_latency_ms",
    ])

    endpoints: List[Endpoint] = list_endpoints(conn)
    for endpoint in endpoints:
        stats = compute_stats(conn, endpoint)
        writer.writerow([
            endpoint.url,
            stats.total_pings,
            stats.success_count,
            stats.failure_count,
            f"{stats.uptime_pct:.1f}" if stats.uptime_pct is not None else "",
            f"{stats.avg_latency_ms:.2f}" if stats.avg_latency_ms is not None else "",
            f"{stats.min_latency_ms:.2f}" if stats.min_latency_ms is not None else "",
            f"{stats.max_latency_ms:.2f}" if stats.max_latency_ms is not None else "",
        ])

    return output.getvalue()
