"""Tests for api_pulse.comparator."""

import sqlite3
import pytest

from api_pulse.db import init_db
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.models import PingResult
from api_pulse.comparator import compare_endpoint, WindowStats


@pytest.fixture()
def tmp_db():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    yield conn
    conn.close()


def _add_ping(conn, url, success, latency_ms):
    result = PingResult(url=url, success=success, latency_ms=latency_ms, error=None)
    save_ping(result, conn=conn)


def test_compare_no_pings(tmp_db):
    add_endpoint("https://empty.example.com", conn=tmp_db)
    result = compare_endpoint("https://empty.example.com", conn=tmp_db)
    assert result.window_a.count == 0
    assert result.window_b.count == 0
    assert result.latency_delta_ms is None
    assert result.success_rate_delta == 0.0


def test_compare_only_recent_pings(tmp_db):
    url = "https://api.example.com"
    add_endpoint(url, conn=tmp_db)
    # Add 5 pings — all go into window_b (newest)
    for _ in range(5):
        _add_ping(tmp_db, url, success=True, latency_ms=100.0)

    result = compare_endpoint(url, window_a_n=10, window_b_n=10, conn=tmp_db)
    assert result.window_b.count == 5
    assert result.window_a.count == 0  # no older pings
    assert result.window_b.avg_latency_ms == pytest.approx(100.0)


def test_compare_latency_delta(tmp_db):
    url = "https://slow.example.com"
    add_endpoint(url, conn=tmp_db)
    # Older pings (window_a) — low latency
    for _ in range(5):
        _add_ping(tmp_db, url, success=True, latency_ms=50.0)
    # Newer pings (window_b) — higher latency
    for _ in range(5):
        _add_ping(tmp_db, url, success=True, latency_ms=150.0)

    result = compare_endpoint(url, window_a_n=5, window_b_n=5, conn=tmp_db)
    assert result.window_a.avg_latency_ms == pytest.approx(50.0)
    assert result.window_b.avg_latency_ms == pytest.approx(150.0)
    assert result.latency_delta_ms == pytest.approx(100.0)


def test_compare_success_rate_delta(tmp_db):
    url = "https://flaky.example.com"
    add_endpoint(url, conn=tmp_db)
    # Older pings (window_a) — all succeed
    for _ in range(4):
        _add_ping(tmp_db, url, success=True, latency_ms=80.0)
    # Newer pings (window_b) — 50 % failure
    for i in range(4):
        _add_ping(tmp_db, url, success=(i % 2 == 0), latency_ms=80.0)

    result = compare_endpoint(url, window_a_n=4, window_b_n=4, conn=tmp_db)
    assert result.window_a.success_rate == pytest.approx(1.0)
    assert result.window_b.success_rate == pytest.approx(0.5)
    assert result.success_rate_delta == pytest.approx(-0.5)


def test_str_representation(tmp_db):
    url = "https://str.example.com"
    add_endpoint(url, conn=tmp_db)
    for _ in range(3):
        _add_ping(tmp_db, url, success=True, latency_ms=200.0)

    result = compare_endpoint(url, window_a_n=3, window_b_n=3, conn=tmp_db)
    text = str(result)
    assert url in text
    assert "latency_delta" in text
    assert "success_rate_delta" in text
