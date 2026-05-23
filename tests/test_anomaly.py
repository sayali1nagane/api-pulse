"""Tests for api_pulse.anomaly."""

from __future__ import annotations

import sqlite3
import pytest

from api_pulse.db import init_db
from api_pulse.models import PingResult
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.baseline import set_baseline, BaselineResult
from api_pulse.anomaly import detect_anomaly, scan_anomalies, Anomaly
from api_pulse.models import Endpoint


@pytest.fixture
def tmp_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()


def _add_pings(conn, url: str, latencies, success=True):
    for ms in latencies:
        save_ping(conn, PingResult(url=url, success=success, latency_ms=ms, status_code=200 if success else None, error=None))


def _set_bl(conn, url, avg):
    """Set a simple baseline with avg and no std stored (avg only)."""
    conn.execute(
        "INSERT OR REPLACE INTO baselines (url, avg_ms, sample_count) VALUES (?, ?, ?)",
        (url, avg, 10),
    )
    conn.commit()


def test_detect_anomaly_no_baseline(tmp_db):
    add_endpoint(tmp_db, Endpoint(url="http://a.test", name="a", interval=60))
    _add_pings(tmp_db, "http://a.test", [100] * 10)
    result = detect_anomaly(tmp_db, "http://a.test", 9999.0)
    assert result is None


def test_detect_anomaly_too_few_pings(tmp_db):
    add_endpoint(tmp_db, Endpoint(url="http://b.test", name="b", interval=60))
    _add_pings(tmp_db, "http://b.test", [100, 102, 98])  # fewer than DEFAULT_MIN_PINGS
    _set_bl(tmp_db, "http://b.test", 100.0)
    result = detect_anomaly(tmp_db, "http://b.test", 9999.0)
    assert result is None


def test_detect_anomaly_no_outlier(tmp_db):
    add_endpoint(tmp_db, Endpoint(url="http://c.test", name="c", interval=60))
    latencies = [100.0] * 10
    _add_pings(tmp_db, "http://c.test", latencies)
    _set_bl(tmp_db, "http://c.test", 100.0)
    # std is 0 when all values are identical — should return None
    result = detect_anomaly(tmp_db, "http://c.test", 105.0)
    assert result is None


def test_detect_anomaly_flags_outlier(tmp_db):
    add_endpoint(tmp_db, Endpoint(url="http://d.test", name="d", interval=60))
    latencies = [100.0, 102.0, 98.0, 101.0, 99.0, 100.0, 101.0]
    _add_pings(tmp_db, "http://d.test", latencies)
    _set_bl(tmp_db, "http://d.test", 100.0)
    result = detect_anomaly(tmp_db, "http://d.test", 500.0, sigma_threshold=2.0)
    assert isinstance(result, Anomaly)
    assert result.url == "http://d.test"
    assert result.sigma > 2.0


def test_scan_anomalies_returns_list(tmp_db):
    add_endpoint(tmp_db, Endpoint(url="http://e.test", name="e", interval=60))
    latencies = [100.0, 102.0, 98.0, 101.0, 99.0, 100.0, 101.0]
    _add_pings(tmp_db, "http://e.test", latencies)
    _set_bl(tmp_db, "http://e.test", 100.0)
    # Last ping was normal — no anomaly expected
    anomalies = scan_anomalies(tmp_db, sigma_threshold=2.0)
    assert isinstance(anomalies, list)


def test_anomaly_str():
    a = Anomaly(url="http://x.test", latency_ms=500.0, baseline_avg_ms=100.0, baseline_std_ms=20.0, sigma=20.0)
    text = str(a)
    assert "ANOMALY" in text
    assert "http://x.test" in text
    assert "20.00σ" in text
