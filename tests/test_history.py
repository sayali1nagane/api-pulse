"""Tests for api_pulse.history latency trend module."""

from __future__ import annotations

import sqlite3
import pytest

from api_pulse.db import init_db
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.models import PingResult
from api_pulse.history import fetch_history, LatencyHistory


@pytest.fixture
def tmp_db():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    yield conn
    conn.close()


def _add_ping(conn, url: str, latency_ms: float | None, ok: bool = True):
    result = PingResult(
        endpoint_url=url,
        status_code=200 if ok else 500,
        latency_ms=latency_ms,
        success=ok,
        error=None,
    )
    save_ping(conn, result)


def test_fetch_history_empty(tmp_db):
    add_endpoint(tmp_db, "https://example.com", "Example")
    hist = fetch_history(tmp_db, "https://example.com", window=10)
    assert hist.url == "https://example.com"
    assert hist.available == 0
    assert hist.average is None
    assert hist.minimum is None
    assert hist.maximum is None
    assert hist.sparkline() == ""


def test_fetch_history_with_data(tmp_db):
    url = "https://api.example.com"
    add_endpoint(tmp_db, url, "API")
    for ms in [100.0, 200.0, 150.0, 300.0, 50.0]:
        _add_ping(tmp_db, url, ms)

    hist = fetch_history(tmp_db, url, window=10)
    assert hist.available == 5
    assert hist.minimum == pytest.approx(50.0)
    assert hist.maximum == pytest.approx(300.0)
    assert hist.average == pytest.approx(160.0)


def test_sparkline_length_matches_pings(tmp_db):
    url = "https://spark.example.com"
    add_endpoint(tmp_db, url, "Spark")
    for ms in [10.0, 20.0, 30.0, 40.0]:
        _add_ping(tmp_db, url, ms)

    hist = fetch_history(tmp_db, url, window=10)
    assert len(hist.sparkline()) == 4


def test_sparkline_failed_pings_show_question_mark(tmp_db):
    url = "https://fail.example.com"
    add_endpoint(tmp_db, url, "Fail")
    _add_ping(tmp_db, url, 100.0, ok=True)
    _add_ping(tmp_db, url, None, ok=False)
    _add_ping(tmp_db, url, 200.0, ok=True)

    hist = fetch_history(tmp_db, url, window=10)
    spark = hist.sparkline()
    assert "?" in spark
    assert len(spark) == 3


def test_window_limits_results(tmp_db):
    url = "https://window.example.com"
    add_endpoint(tmp_db, url, "Window")
    for ms in range(1, 16):  # 15 pings
        _add_ping(tmp_db, url, float(ms * 10))

    hist = fetch_history(tmp_db, url, window=5)
    assert hist.available == 5
    assert len(hist.latencies) == 5


def test_str_representation(tmp_db):
    url = "https://str.example.com"
    add_endpoint(tmp_db, url, "Str")
    _add_ping(tmp_db, url, 123.0)

    hist = fetch_history(tmp_db, url, window=10)
    text = str(hist)
    assert url in text
    assert "avg=" in text
    assert "min=" in text
    assert "max=" in text
    assert "samples=" in text
