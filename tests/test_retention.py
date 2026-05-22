"""Tests for api_pulse.retention."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta
from typing import Generator

import pytest

from api_pulse.db import init_db
from api_pulse.retention import prune_pings, prune_stats


@pytest.fixture()
def tmp_db(monkeypatch: pytest.MonkeyPatch) -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    monkeypatch.setattr("api_pulse.retention.db_session", lambda: _ctx(conn))
    yield conn
    conn.close()


class _ctx:
    """Minimal context-manager wrapper around an existing connection."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn

    def __enter__(self) -> sqlite3.Connection:
        return self._conn

    def __exit__(self, *_: object) -> None:
        self._conn.commit()


def _insert_ping(conn: sqlite3.Connection, url: str, days_ago: float) -> None:
    ts = (datetime.utcnow() - timedelta(days=days_ago)).isoformat()
    conn.execute(
        "INSERT INTO pings (endpoint_url, timestamp, status_code, latency_ms, success)"
        " VALUES (?, ?, 200, 50.0, 1)",
        (url, ts),
    )
    conn.commit()


def test_prune_removes_old_records(tmp_db: sqlite3.Connection) -> None:
    _insert_ping(tmp_db, "https://a.example.com", days_ago=10)
    _insert_ping(tmp_db, "https://a.example.com", days_ago=1)
    deleted = prune_pings(days=7)
    assert deleted == 1
    remaining = tmp_db.execute("SELECT COUNT(*) FROM pings").fetchone()[0]
    assert remaining == 1


def test_prune_by_url_only_affects_that_url(tmp_db: sqlite3.Connection) -> None:
    _insert_ping(tmp_db, "https://a.example.com", days_ago=10)
    _insert_ping(tmp_db, "https://b.example.com", days_ago=10)
    deleted = prune_pings(days=7, url="https://a.example.com")
    assert deleted == 1
    remaining = tmp_db.execute("SELECT COUNT(*) FROM pings").fetchone()[0]
    assert remaining == 1


def test_prune_zero_days_raises(tmp_db: sqlite3.Connection) -> None:  # noqa: ARG001
    with pytest.raises(ValueError):
        prune_pings(days=0)


def test_prune_stats_returns_counts(tmp_db: sqlite3.Connection) -> None:
    _insert_ping(tmp_db, "https://a.example.com", days_ago=1)
    _insert_ping(tmp_db, "https://a.example.com", days_ago=2)
    _insert_ping(tmp_db, "https://b.example.com", days_ago=1)
    stats = prune_stats()
    assert stats["https://a.example.com"] == 2
    assert stats["https://b.example.com"] == 1


def test_prune_stats_empty(tmp_db: sqlite3.Connection) -> None:  # noqa: ARG001
    assert prune_stats() == {}
