"""Tests for api_pulse.trend."""

import sqlite3
import pytest
from datetime import datetime, timezone

from api_pulse.db import init_db
from api_pulse.models import Endpoint
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.trend import analyze_trend, analyze_all, _linear_slope


@pytest.fixture
def tmp_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()


def _add_ping(conn, url: str, latency_ms: float | None, success: bool = True):
    from api_pulse.models import PingResult
    result = PingResult(
        url=url,
        timestamp=datetime.now(timezone.utc).isoformat(),
        latency_ms=latency_ms,
        status_code=200 if success else 500,
        success=success,
        error=None,
    )
    save_ping(conn, result)


def _make_endpoint(url: str) -> Endpoint:
    return Endpoint(id=None, url=url, name="test", interval_seconds=60)


# --- _linear_slope ---

def test_linear_slope_flat():
    assert _linear_slope([10.0, 10.0, 10.0]) == pytest.approx(0.0)


def test_linear_slope_increasing():
    slope = _linear_slope([1.0, 2.0, 3.0])
    assert slope > 0


def test_linear_slope_decreasing():
    slope = _linear_slope([3.0, 2.0, 1.0])
    assert slope < 0


# --- analyze_trend ---

def test_trend_insufficient_data(tmp_db):
    add_endpoint(tmp_db, "http://a.test", "A", 60)
    _add_ping(tmp_db, "http://a.test", 100.0)
    _add_ping(tmp_db, "http://a.test", 110.0)

    result = analyze_trend(tmp_db, "http://a.test")
    assert result.direction == "insufficient_data"
    assert result.moving_avg_ms is None
    assert result.slope_ms_per_ping is None


def test_trend_stable(tmp_db):
    add_endpoint(tmp_db, "http://b.test", "B", 60)
    for ms in [100.0, 101.0, 100.5, 99.5, 100.0]:
        _add_ping(tmp_db, "http://b.test", ms)

    result = analyze_trend(tmp_db, "http://b.test", stable_threshold_ms=5.0)
    assert result.direction == "stable"
    assert result.moving_avg_ms == pytest.approx(100.2)


def test_trend_degrading(tmp_db):
    add_endpoint(tmp_db, "http://c.test", "C", 60)
    for ms in [50.0, 100.0, 150.0, 200.0, 250.0]:
        _add_ping(tmp_db, "http://c.test", ms)

    result = analyze_trend(tmp_db, "http://c.test", stable_threshold_ms=5.0)
    assert result.direction == "degrading"
    assert result.slope_ms_per_ping > 0


def test_trend_improving(tmp_db):
    add_endpoint(tmp_db, "http://d.test", "D", 60)
    for ms in [250.0, 200.0, 150.0, 100.0, 50.0]:
        _add_ping(tmp_db, "http://d.test", ms)

    result = analyze_trend(tmp_db, "http://d.test", stable_threshold_ms=5.0)
    assert result.direction == "improving"
    assert result.slope_ms_per_ping < 0


def test_trend_skips_failed_pings(tmp_db):
    add_endpoint(tmp_db, "http://e.test", "E", 60)
    for ms in [100.0, 105.0, 102.0]:
        _add_ping(tmp_db, "http://e.test", ms)
    _add_ping(tmp_db, "http://e.test", None, success=False)

    result = analyze_trend(tmp_db, "http://e.test")
    assert result.sample_count == 3


def test_analyze_all(tmp_db):
    for url in ["http://x.test", "http://y.test"]:
        add_endpoint(tmp_db, url, "ep", 60)
        for ms in [80.0, 90.0, 85.0]:
            _add_ping(tmp_db, url, ms)

    endpoints = [_make_endpoint("http://x.test"), _make_endpoint("http://y.test")]
    results = analyze_all(tmp_db, endpoints)
    assert len(results) == 2
    assert all(r.direction != "insufficient_data" for r in results)


def test_trend_str_insufficient():
    from api_pulse.trend import TrendResult
    r = TrendResult(url="http://z.test", sample_count=1, moving_avg_ms=None,
                    slope_ms_per_ping=None, direction="insufficient_data")
    assert "insufficient data" in str(r)


def test_trend_str_degrading():
    from api_pulse.trend import TrendResult
    r = TrendResult(url="http://z.test", sample_count=10, moving_avg_ms=200.0,
                    slope_ms_per_ping=12.5, direction="degrading")
    assert "degrading" in str(r)
    assert "↑" in str(r)
