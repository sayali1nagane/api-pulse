"""Tests for the reporter module."""

import pytest
import sqlite3
from api_pulse.db import init_db
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.reporter import compute_stats, report_all


@pytest.fixture
def tmp_db(tmp_path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()


def test_compute_stats_no_pings(tmp_db):
    add_endpoint(tmp_db, "https://example.com", "example")
    stats = compute_stats(tmp_db, "https://example.com", "example")
    assert stats.total_pings == 0
    assert stats.uptime_pct == 0.0
    assert stats.avg_latency_ms is None


def test_compute_stats_all_success(tmp_db):
    add_endpoint(tmp_db, "https://example.com", "example")
    for latency in [100.0, 200.0, 150.0]:
        save_ping(tmp_db, "https://example.com", success=True, latency_ms=latency, status_code=200)

    stats = compute_stats(tmp_db, "https://example.com", "example")
    assert stats.total_pings == 3
    assert stats.success_count == 3
    assert stats.failure_count == 0
    assert stats.uptime_pct == 100.0
    assert stats.avg_latency_ms == pytest.approx(150.0)
    assert stats.min_latency_ms == pytest.approx(100.0)
    assert stats.max_latency_ms == pytest.approx(200.0)


def test_compute_stats_mixed(tmp_db):
    add_endpoint(tmp_db, "https://api.io", "api")
    save_ping(tmp_db, "https://api.io", success=True, latency_ms=80.0, status_code=200)
    save_ping(tmp_db, "https://api.io", success=False, latency_ms=None, status_code=None)
    save_ping(tmp_db, "https://api.io", success=True, latency_ms=120.0, status_code=200)

    stats = compute_stats(tmp_db, "https://api.io", "api")
    assert stats.total_pings == 3
    assert stats.success_count == 2
    assert stats.failure_count == 1
    assert stats.uptime_pct == pytest.approx(66.666, rel=1e-2)
    assert stats.avg_latency_ms == pytest.approx(100.0)


def test_report_all_multiple_endpoints(tmp_db):
    add_endpoint(tmp_db, "https://a.com", "a")
    add_endpoint(tmp_db, "https://b.com", "b")
    save_ping(tmp_db, "https://a.com", success=True, latency_ms=50.0, status_code=200)
    save_ping(tmp_db, "https://b.com", success=False, latency_ms=None, status_code=503)

    results = report_all(tmp_db)
    assert len(results) == 2
    urls = {r.url for r in results}
    assert "https://a.com" in urls
    assert "https://b.com" in urls


def test_endpoint_stats_str(tmp_db):
    add_endpoint(tmp_db, "https://example.com", "example")
    save_ping(tmp_db, "https://example.com", success=True, latency_ms=99.5, status_code=200)
    stats = compute_stats(tmp_db, "https://example.com", "example")
    output = str(stats)
    assert "example" in output
    assert "uptime=100.0%" in output
    assert "avg=99.5ms" in output
