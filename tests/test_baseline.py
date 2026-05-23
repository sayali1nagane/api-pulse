"""Tests for api_pulse.baseline module."""

import sqlite3
from datetime import datetime, timezone

import pytest

from api_pulse.db import init_db
from api_pulse.baseline import (
    ensure_baselines_table,
    set_baseline,
    get_baseline,
    compute_baseline_from_history,
    check_baseline,
    BaselineResult,
)
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.models import PingResult


@pytest.fixture()
def tmp_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    ensure_baselines_table(conn)
    yield conn
    conn.close()


def _add_ping(conn, url: str, latency_ms: float, success: bool = True) -> None:
    add_endpoint(conn, url, interval=60)
    save_ping(
        conn,
        PingResult(
            url=url,
            success=success,
            status_code=200 if success else 500,
            latency_ms=latency_ms if success else None,
            error=None if success else "err",
            checked_at=datetime.now(timezone.utc).isoformat(),
        ),
    )


def test_set_and_get_baseline(tmp_db):
    set_baseline(tmp_db, "http://example.com", 120.5)
    result = get_baseline(tmp_db, "http://example.com")
    assert result == pytest.approx(120.5)


def test_get_baseline_missing_returns_none(tmp_db):
    assert get_baseline(tmp_db, "http://missing.com") is None


def test_set_baseline_updates_existing(tmp_db):
    set_baseline(tmp_db, "http://example.com", 100.0)
    set_baseline(tmp_db, "http://example.com", 200.0)
    assert get_baseline(tmp_db, "http://example.com") == pytest.approx(200.0)


def test_compute_baseline_from_history(tmp_db):
    url = "http://api.test"
    for ms in [100.0, 200.0, 300.0]:
        _add_ping(tmp_db, url, latency_ms=ms)
    avg = compute_baseline_from_history(tmp_db, url, n=10)
    assert avg == pytest.approx(200.0)
    assert get_baseline(tmp_db, url) == pytest.approx(200.0)


def test_compute_baseline_no_successful_pings_returns_none(tmp_db):
    url = "http://failing.test"
    _add_ping(tmp_db, url, latency_ms=0.0, success=False)
    result = compute_baseline_from_history(tmp_db, url, n=10)
    assert result is None


def test_check_baseline_degraded(tmp_db):
    url = "http://slow.test"
    set_baseline(tmp_db, url, 100.0)
    for ms in [150.0, 160.0, 170.0]:
        _add_ping(tmp_db, url, latency_ms=ms)
    result = check_baseline(tmp_db, url, n=10)
    assert result is not None
    assert result.degraded is True
    assert result.delta_ms > 0


def test_check_baseline_ok(tmp_db):
    url = "http://fast.test"
    set_baseline(tmp_db, url, 200.0)
    for ms in [190.0, 200.0, 210.0]:
        _add_ping(tmp_db, url, latency_ms=ms)
    result = check_baseline(tmp_db, url, n=10)
    assert result is not None
    assert result.degraded is False


def test_check_baseline_no_stored_baseline_returns_none(tmp_db):
    url = "http://nobaseline.test"
    _add_ping(tmp_db, url, latency_ms=100.0)
    assert check_baseline(tmp_db, url) is None


def test_baseline_result_str_contains_status(tmp_db):
    br = BaselineResult(url="http://x.test", baseline_ms=100.0, current_ms=130.0)
    text = str(br)
    assert "DEGRADED" in text
    assert "http://x.test" in text
