"""Periodic digest: summarise recent ping activity into a human-readable report."""

from __future__ import annotations

import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional

from .db import db_session
from .repository import list_endpoints, get_recent_pings


@dataclass
class DigestEntry:
    url: str
    total: int
    successes: int
    avg_latency_ms: Optional[float]
    min_latency_ms: Optional[float]
    max_latency_ms: Optional[float]
    window_hours: int

    @property
    def success_rate(self) -> float:
        return (self.successes / self.total * 100) if self.total else 0.0

    def __str__(self) -> str:
        lat = (
            f"avg={self.avg_latency_ms:.1f}ms  "
            f"min={self.min_latency_ms:.1f}ms  "
            f"max={self.max_latency_ms:.1f}ms"
            if self.avg_latency_ms is not None
            else "no latency data"
        )
        return (
            f"  {self.url}\n"
            f"    pings={self.total}  ok={self.successes}  "
            f"success={self.success_rate:.1f}%  {lat}"
        )


@dataclass
class Digest:
    generated_at: datetime
    window_hours: int
    entries: List[DigestEntry] = field(default_factory=list)

    def __str__(self) -> str:
        header = (
            f"=== API-Pulse Digest ===\n"
            f"Generated : {self.generated_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"Window    : last {self.window_hours}h\n"
            f"Endpoints : {len(self.entries)}\n"
        )
        if not self.entries:
            return header + "  (no data)\n"
        body = "\n".join(str(e) for e in self.entries)
        return header + body + "\n"


def build_digest(conn, window_hours: int = 24, limit: int = 500) -> Digest:
    """Build a Digest for all endpoints using pings from the last *window_hours*."""
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=window_hours)
    endpoints = list_endpoints(conn)
    entries: List[DigestEntry] = []

    for ep in endpoints:
        pings = [
            p for p in get_recent_pings(conn, ep.url, limit=limit)
            if p.checked_at >= cutoff
        ]
        total = len(pings)
        successes = sum(1 for p in pings if p.success)
        latencies = [p.latency_ms for p in pings if p.latency_ms is not None]
        entries.append(DigestEntry(
            url=ep.url,
            total=total,
            successes=successes,
            avg_latency_ms=sum(latencies) / len(latencies) if latencies else None,
            min_latency_ms=min(latencies) if latencies else None,
            max_latency_ms=max(latencies) if latencies else None,
            window_hours=window_hours,
        ))

    return Digest(generated_at=now, window_hours=window_hours, entries=entries)
