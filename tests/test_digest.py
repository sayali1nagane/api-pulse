"""Tests for api_pulse.digest."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

import pytest

from api_pulse.db import init_db
from api_pulse.digest import build_digest, Digest, DigestEntry
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.models import PingResult


@pytest.fixture
def tmp_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()


def _add_ping(conn, url: str, success: bool, latency_ms: float, ago_seconds: int = 0):
    ts = datetime.utcnow() - timedelta(seconds=ago_seconds)
    result = PingResult(url=url, success=success, latency_ms=latency_ms,
                        status_code=200 if success else 500,
                        error=None, checked_at=ts)
    save_ping(conn, result)


def test_digest_empty_no_endpoints(tmp_db):
    digest = build_digest(tmp_db, window_hours=24)
    assert isinstance(digest, Digest)
    assert digest.entries == []
    assert "no data" in str(digest)


def test_digest_single_endpoint_all_success(tmp_db):
    add_endpoint(tmp_db, "https://example.com", "example")
    for i in range(5):
        _add_ping(tmp_db, "https://example.com", True, 100.0 + i * 10)

    digest = build_digest(tmp_db, window_hours=24)
    assert len(digest.entries) == 1
    entry = digest.entries[0]
    assert entry.total == 5
    assert entry.successes == 5
    assert entry.success_rate == 100.0
    assert entry.avg_latency_ms == pytest.approx(120.0)
    assert entry.min_latency_ms == pytest.approx(100.0)
    assert entry.max_latency_ms == pytest.approx(140.0)


def test_digest_mixed_success_failure(tmp_db):
    add_endpoint(tmp_db, "https://api.test", "test")
    _add_ping(tmp_db, "https://api.test", True, 200.0)
    _add_ping(tmp_db, "https://api.test", False, None)
    _add_ping(tmp_db, "https://api.test", True, 400.0)

    digest = build_digest(tmp_db, window_hours=24)
    entry = digest.entries[0]
    assert entry.total == 3
    assert entry.successes == 2
    assert entry.success_rate == pytest.approx(66.67, rel=1e-2)
    assert entry.avg_latency_ms == pytest.approx(300.0)


def test_digest_excludes_old_pings(tmp_db):
    add_endpoint(tmp_db, "https://old.test", "old")
    # ping within window
    _add_ping(tmp_db, "https://old.test", True, 50.0, ago_seconds=3600)
    # ping outside window (25 h ago)
    _add_ping(tmp_db, "https://old.test", True, 999.0, ago_seconds=25 * 3600)

    digest = build_digest(tmp_db, window_hours=24)
    entry = digest.entries[0]
    assert entry.total == 1
    assert entry.avg_latency_ms == pytest.approx(50.0)


def test_digest_str_contains_url(tmp_db):
    add_endpoint(tmp_db, "https://check.io", "check")
    _add_ping(tmp_db, "https://check.io", True, 77.0)
    digest = build_digest(tmp_db, window_hours=24)
    text = str(digest)
    assert "https://check.io" in text
    assert "success=100.0%" in text


def test_digest_entry_no_latency_str():
    entry = DigestEntry(
        url="https://x.com", total=1, successes=0,
        avg_latency_ms=None, min_latency_ms=None, max_latency_ms=None,
        window_hours=24,
    )
    assert "no latency data" in str(entry)
