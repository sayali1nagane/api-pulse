"""Snapshot module: capture and compare endpoint status at a point in time."""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import List, Optional

from api_pulse.db import db_session
from api_pulse.repository import list_endpoints, get_recent_pings


@dataclass
class EndpointSnapshot:
    url: str
    captured_at: str
    total_pings: int
    success_count: int
    failure_count: int
    avg_latency_ms: Optional[float]
    last_status: Optional[int]

    @property
    def success_rate(self) -> float:
        if self.total_pings == 0:
            return 0.0
        return self.success_count / self.total_pings

    def __str__(self) -> str:
        rate = f"{self.success_rate * 100:.1f}%"
        lat = f"{self.avg_latency_ms:.1f} ms" if self.avg_latency_ms is not None else "n/a"
        return (
            f"{self.url} | captured={self.captured_at} | "
            f"pings={self.total_pings} ok={self.success_count} "
            f"fail={self.failure_count} rate={rate} avg_lat={lat}"
        )


def capture_snapshot(conn, limit: int = 100) -> List[EndpointSnapshot]:
    """Capture a snapshot of all endpoints using recent ping history."""
    snapshots: List[EndpointSnapshot] = []
    now = datetime.now(timezone.utc).isoformat()

    endpoints = list_endpoints(conn)
    for ep in endpoints:
        pings = get_recent_pings(conn, ep.url, limit=limit)
        total = len(pings)
        success = sum(1 for p in pings if p.success)
        failure = total - success
        latencies = [p.latency_ms for p in pings if p.success and p.latency_ms is not None]
        avg_lat = sum(latencies) / len(latencies) if latencies else None
        last_status = pings[0].status_code if pings else None

        snapshots.append(EndpointSnapshot(
            url=ep.url,
            captured_at=now,
            total_pings=total,
            success_count=success,
            failure_count=failure,
            avg_latency_ms=avg_lat,
            last_status=last_status,
        ))

    return snapshots


def snapshot_to_json(snapshots: List[EndpointSnapshot]) -> str:
    """Serialise a list of snapshots to a JSON string."""
    return json.dumps([asdict(s) for s in snapshots], indent=2)


def diff_snapshots(
    before: List[EndpointSnapshot],
    after: List[EndpointSnapshot],
) -> List[str]:
    """Return human-readable diff lines between two snapshots."""
    before_map = {s.url: s for s in before}
    after_map = {s.url: s for s in after}
    lines: List[str] = []

    for url, a in after_map.items():
        b = before_map.get(url)
        if b is None:
            lines.append(f"[NEW]  {url}")
            continue
        changes = []
        if b.success_rate != a.success_rate:
            changes.append(
                f"success_rate {b.success_rate*100:.1f}% -> {a.success_rate*100:.1f}%"
            )
        if b.avg_latency_ms is not None and a.avg_latency_ms is not None:
            delta = a.avg_latency_ms - b.avg_latency_ms
            if abs(delta) >= 1.0:
                changes.append(f"avg_latency {b.avg_latency_ms:.1f} -> {a.avg_latency_ms:.1f} ms")
        if changes:
            lines.append(f"[DIFF] {url}: " + "; ".join(changes))

    for url in before_map:
        if url not in after_map:
            lines.append(f"[GONE] {url}")

    return lines
