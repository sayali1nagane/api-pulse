"""Baseline latency management: store and compare per-endpoint latency baselines."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import Optional

from api_pulse.db import db_session
from api_pulse.repository import get_recent_pings


def ensure_baselines_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS baselines (
            url        TEXT PRIMARY KEY,
            latency_ms REAL NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


@dataclass
class BaselineResult:
    url: str
    baseline_ms: float
    current_ms: float

    @property
    def delta_ms(self) -> float:
        return self.current_ms - self.baseline_ms

    @property
    def degraded(self) -> bool:
        """True when current average exceeds baseline by more than 20 %."""
        return self.current_ms > self.baseline_ms * 1.20

    def __str__(self) -> str:
        status = "DEGRADED" if self.degraded else "OK"
        return (
            f"{self.url}: baseline={self.baseline_ms:.1f}ms "
            f"current={self.current_ms:.1f}ms "
            f"delta={self.delta_ms:+.1f}ms [{status}]"
        )


def set_baseline(conn: sqlite3.Connection, url: str, latency_ms: float) -> None:
    ensure_baselines_table(conn)
    conn.execute(
        """
        INSERT INTO baselines (url, latency_ms, updated_at)
        VALUES (?, ?, datetime('now'))
        ON CONFLICT(url) DO UPDATE SET latency_ms=excluded.latency_ms,
                                       updated_at=excluded.updated_at
        """,
        (url, latency_ms),
    )
    conn.commit()


def get_baseline(conn: sqlite3.Connection, url: str) -> Optional[float]:
    ensure_baselines_table(conn)
    row = conn.execute(
        "SELECT latency_ms FROM baselines WHERE url = ?", (url,)
    ).fetchone()
    return row[0] if row else None


def compute_baseline_from_history(conn: sqlite3.Connection, url: str, n: int = 20) -> Optional[float]:
    """Compute average latency over the last *n* successful pings and persist it."""
    pings = get_recent_pings(conn, url, limit=n)
    successful = [p.latency_ms for p in pings if p.success and p.latency_ms is not None]
    if not successful:
        return None
    avg = sum(successful) / len(successful)
    set_baseline(conn, url, avg)
    return avg


def check_baseline(conn: sqlite3.Connection, url: str, n: int = 10) -> Optional[BaselineResult]:
    """Compare recent average latency against stored baseline."""
    baseline_ms = get_baseline(conn, url)
    if baseline_ms is None:
        return None
    pings = get_recent_pings(conn, url, limit=n)
    successful = [p.latency_ms for p in pings if p.success and p.latency_ms is not None]
    if not successful:
        return None
    current_ms = sum(successful) / len(successful)
    return BaselineResult(url=url, baseline_ms=baseline_ms, current_ms=current_ms)
