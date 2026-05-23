"""Hourly latency heatmap: buckets average latency by hour-of-day."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from api_pulse.db import db_session


@dataclass
class HeatmapRow:
    """Average latency statistics for a single hour bucket (0-23)."""

    hour: int  # 0-23
    sample_count: int
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float

    def bar(self, width: int = 20) -> str:
        """Return a simple ASCII bar proportional to avg_latency_ms."""
        max_possible = 2000.0  # treat 2 s as full bar
        filled = int(min(self.avg_latency_ms / max_possible, 1.0) * width)
        return "█" * filled + "░" * (width - filled)

    def __str__(self) -> str:  # pragma: no cover
        return (
            f"{self.hour:02d}:00  {self.bar()}  "
            f"avg={self.avg_latency_ms:.1f}ms  "
            f"min={self.min_latency_ms:.1f}ms  "
            f"max={self.max_latency_ms:.1f}ms  "
            f"n={self.sample_count}"
        )


def build_heatmap(
    url: str,
    *,
    days: int = 7,
    conn=None,
) -> List[HeatmapRow]:
    """Return a list of HeatmapRow (one per hour that has data) for *url*.

    Only successful pings (status_code != NULL and latency_ms > 0) from the
    last *days* days are considered.
    """
    query = """
        SELECT
            CAST(strftime('%H', checked_at) AS INTEGER) AS hour,
            COUNT(*)                                    AS n,
            AVG(latency_ms)                             AS avg_ms,
            MIN(latency_ms)                             AS min_ms,
            MAX(latency_ms)                             AS max_ms
        FROM pings
        WHERE endpoint_url = ?
          AND success = 1
          AND checked_at >= datetime('now', ? || ' days')
        GROUP BY hour
        ORDER BY hour
    """
    days_param = f"-{days}"

    def _run(c):
        rows = c.execute(query, (url, days_param)).fetchall()
        return [
            HeatmapRow(
                hour=r[0],
                sample_count=r[1],
                avg_latency_ms=round(r[2], 3),
                min_latency_ms=round(r[3], 3),
                max_latency_ms=round(r[4], 3),
            )
            for r in rows
        ]

    if conn is not None:
        return _run(conn)
    with db_session() as c:
        return _run(c)


def heatmap_all(*, days: int = 7, conn=None) -> Dict[str, List[HeatmapRow]]:
    """Return heatmaps for every endpoint that has ping data."""
    def _urls(c):
        return [r[0] for r in c.execute("SELECT DISTINCT endpoint_url FROM pings").fetchall()]

    if conn is not None:
        urls = _urls(conn)
        return {url: build_heatmap(url, days=days, conn=conn) for url in urls}

    with db_session() as c:
        urls = _urls(c)
    return {url: build_heatmap(url, days=days) for url in urls}
