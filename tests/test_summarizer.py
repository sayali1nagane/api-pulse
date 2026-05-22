"""Tests for api_pulse.summarizer."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

import pytest

from api_pulse.db import init_db
from api_pulse.models import PingResult
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.summarizer import summarize_all, summarize_endpoint


@pytest.fixture()
def tmp_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()


def _add_ping(conn, url: str, success: bool, latency_ms: float, hours_ago: float = 0.5):
    ts = datetime.utcnow() - timedelta(hours=hours_ago)
    result = PingResult(url=url, success=success, latency_ms=latency_ms, timestamp=ts)
    save_ping(conn, result)


def test_summarize_endpoint_no_data(tmp_db):
    add_endpoint(tmp_db, "https://example.com", interval=60)
    entry = summarize_endpoint(tmp_db, "https://example.com", period_hours=24)
    assert entry is None


def test_summarize_endpoint_all_success(tmp_db):
    url = "https://api.example.com"
    add_endpoint(tmp_db, url, interval=60)
    for _ in range(5):
        _add_ping(tmp_db, url, success=True, latency_ms=100.0)

    entry = summarize_endpoint(tmp_db, url, period_hours=24)
    assert entry is not None
    assert entry.total_pings == 5
    assert entry.success_count == 5
    assert entry.failure_count == 0
    assert entry.uptime_pct == pytest.approx(100.0)
    assert entry.avg_latency_ms == pytest.approx(100.0)


def test_summarize_endpoint_mixed(tmp_db):
    url = "https://api.example.com/mixed"
    add_endpoint(tmp_db, url, interval=60)
    _add_ping(tmp_db, url, success=True, latency_ms=200.0)
    _add_ping(tmp_db, url, success=True, latency_ms=400.0)
    _add_ping(tmp_db, url, success=False, latency_ms=0.0)

    entry = summarize_endpoint(tmp_db, url, period_hours=24)
    assert entry is not None
    assert entry.failure_count == 1
    assert entry.uptime_pct == pytest.approx(200 / 3 * 100 / 100 * 100 / 100, abs=1)
    assert entry.avg_latency_ms == pytest.approx(300.0)


def test_summarize_excludes_old_pings(tmp_db):
    url = "https://old.example.com"
    add_endpoint(tmp_db, url, interval=60)
    _add_ping(tmp_db, url, success=True, latency_ms=50.0, hours_ago=0.5)
    _add_ping(tmp_db, url, success=True, latency_ms=50.0, hours_ago=25.0)  # outside window

    entry = summarize_endpoint(tmp_db, url, period_hours=24)
    assert entry is not None
    assert entry.total_pings == 1


def test_summarize_all_multiple_endpoints(tmp_db):
    for i in range(3):
        url = f"https://svc{i}.example.com"
        add_endpoint(tmp_db, url, interval=60)
        _add_ping(tmp_db, url, success=True, latency_ms=float(50 * (i + 1)))

    entries = summarize_all(tmp_db, period_hours=24)
    assert len(entries) == 3
    urls = {e.url for e in entries}
    assert "https://svc0.example.com" in urls


def test_str_representation(tmp_db):
    url = "https://str.example.com"
    add_endpoint(tmp_db, url, interval=60)
    _add_ping(tmp_db, url, success=True, latency_ms=123.4)

    entry = summarize_endpoint(tmp_db, url, period_hours=24)
    assert entry is not None
    text = str(entry)
    assert url in text
    assert "123.4ms" in text
    assert "100.0%" in text
