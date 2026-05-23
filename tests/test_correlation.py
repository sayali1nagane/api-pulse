"""Tests for api_pulse.correlation."""
from __future__ import annotations

import sqlite3
import time
import pytest

from api_pulse.db import init_db
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.models import PingResult
from api_pulse.correlation import correlate_endpoints, correlate_all, _pearson


@pytest.fixture
def tmp_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()


def _add_pings(conn, url: str, latencies):
    add_endpoint(conn, url, interval=60)
    ts = time.time()
    for i, lat in enumerate(latencies):
        pr = PingResult(
            endpoint_url=url,
            timestamp=ts + i,
            status_code=200 if lat is not None else None,
            latency_ms=lat,
            success=lat is not None,
            error=None,
        )
        save_ping(conn, pr)


def test_pearson_perfect_positive():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [2.0, 4.0, 6.0, 8.0, 10.0]
    r = _pearson(xs, ys)
    assert r is not None
    assert abs(r - 1.0) < 1e-9


def test_pearson_perfect_negative():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [10.0, 8.0, 6.0, 4.0, 2.0]
    r = _pearson(xs, ys)
    assert r is not None
    assert abs(r + 1.0) < 1e-9


def test_pearson_insufficient_data():
    assert _pearson([1.0], [2.0]) is None
    assert _pearson([1.0, 2.0], [3.0, 4.0]) is None


def test_correlate_endpoints_insufficient_data(tmp_db):
    _add_pings(tmp_db, "http://a.test", [100.0, 200.0])
    _add_pings(tmp_db, "http://b.test", [110.0, 190.0])
    result = correlate_endpoints(tmp_db, "http://a.test", "http://b.test")
    assert result.coefficient is None
    assert result.sample_size == 2


def test_correlate_endpoints_strong_positive(tmp_db):
    lats = [float(x * 10) for x in range(1, 11)]
    _add_pings(tmp_db, "http://a.test", lats)
    _add_pings(tmp_db, "http://b.test", [l * 2 for l in lats])
    result = correlate_endpoints(tmp_db, "http://a.test", "http://b.test")
    assert result.coefficient is not None
    assert result.coefficient > 0.99
    assert "strong" in str(result)


def test_correlate_all_no_endpoints(tmp_db):
    results = correlate_all(tmp_db)
    assert results == []


def test_correlate_all_single_endpoint(tmp_db):
    _add_pings(tmp_db, "http://only.test", [100.0] * 5)
    results = correlate_all(tmp_db)
    assert results == []


def test_correlate_all_two_endpoints(tmp_db):
    lats = [float(i * 5) for i in range(1, 11)]
    _add_pings(tmp_db, "http://a.test", lats)
    _add_pings(tmp_db, "http://b.test", lats)
    results = correlate_all(tmp_db)
    assert len(results) == 1
    assert results[0].url_a == "http://a.test"
    assert results[0].url_b == "http://b.test"
