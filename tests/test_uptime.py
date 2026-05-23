"""Tests for api_pulse.uptime."""
import time
import sqlite3
import pytest

from api_pulse.db import init_db
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.models import PingResult
from api_pulse.uptime import compute_uptime, compute_all_uptime, UptimeResult


@pytest.fixture
def tmp_db():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    yield conn
    conn.close()


def _add_ping(conn, url: str, success: bool, offset_secs: int = 0):
    """Insert a ping with timestamp relative to now."""
    ts = time.time() - offset_secs
    ping = PingResult(url=url, status_code=200 if success else 500,
                      latency_ms=50.0, success=success, timestamp=ts)
    save_ping(conn, ping)


def test_compute_uptime_no_pings(tmp_db):
    add_endpoint(tmp_db, "https://example.com", 60)
    result = compute_uptime("https://example.com", tmp_db, window_hours=24)
    assert result is None


def test_compute_uptime_all_success(tmp_db):
    url = "https://api.example.com"
    add_endpoint(tmp_db, url, 60)
    for i in range(5):
        _add_ping(tmp_db, url, success=True, offset_secs=i * 60)

    result = compute_uptime(url, tmp_db, window_hours=24)
    assert result is not None
    assert result.total_pings == 5
    assert result.successful_pings == 5
    assert result.uptime_pct == 100.0


def test_compute_uptime_partial_success(tmp_db):
    url = "https://api.example.com"
    add_endpoint(tmp_db, url, 60)
    for i in range(3):
        _add_ping(tmp_db, url, success=True, offset_secs=i * 60)
    for i in range(3, 6):
        _add_ping(tmp_db, url, success=False, offset_secs=i * 60)

    result = compute_uptime(url, tmp_db, window_hours=24)
    assert result is not None
    assert result.total_pings == 6
    assert result.successful_pings == 3
    assert abs(result.uptime_pct - 50.0) < 0.01


def test_compute_uptime_excludes_old_pings(tmp_db):
    url = "https://old.example.com"
    add_endpoint(tmp_db, url, 60)
    # 2 recent pings (within 1 h)
    _add_ping(tmp_db, url, success=True, offset_secs=100)
    _add_ping(tmp_db, url, success=True, offset_secs=200)
    # 1 old ping (> 1 h ago)
    _add_ping(tmp_db, url, success=False, offset_secs=7200)

    result = compute_uptime(url, tmp_db, window_hours=1)
    assert result is not None
    assert result.total_pings == 2
    assert result.successful_pings == 2


def test_compute_all_uptime_multiple_endpoints(tmp_db):
    for url in ["https://a.com", "https://b.com"]:
        add_endpoint(tmp_db, url, 60)
        _add_ping(tmp_db, url, success=True)

    results = compute_all_uptime(tmp_db, window_hours=24)
    urls = {r.url for r in results}
    assert "https://a.com" in urls
    assert "https://b.com" in urls


def test_uptime_result_str():
    r = UptimeResult(url="https://x.com", total_pings=10,
                     successful_pings=9, uptime_pct=90.0, window_hours=24)
    text = str(r)
    assert "https://x.com" in text
    assert "90.00%" in text
    assert "9/10" in text
