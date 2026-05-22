"""Tests for api_pulse.exporter module."""

import sqlite3
import pytest
from datetime import datetime, timezone

from api_pulse.db import init_db
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.models import PingResult
from api_pulse.exporter import export_pings_csv, export_stats_csv


@pytest.fixture
def tmp_db():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    yield conn
    conn.close()


def _add_ping(conn, endpoint_id, status_code, latency_ms, error=None):
    result = PingResult(
        endpoint_id=endpoint_id,
        checked_at=datetime.now(timezone.utc).isoformat(),
        status_code=status_code,
        latency_ms=latency_ms,
        error=error,
    )
    save_ping(conn, result)


def test_export_pings_csv_empty(tmp_db):
    csv_output = export_pings_csv(tmp_db)
    lines = csv_output.strip().splitlines()
    assert len(lines) == 1
    assert lines[0] == "url,checked_at,status_code,latency_ms,error"


def test_export_pings_csv_with_data(tmp_db):
    ep = add_endpoint(tmp_db, "https://example.com", interval=60)
    _add_ping(tmp_db, ep.id, 200, 123.4)
    _add_ping(tmp_db, ep.id, 500, 88.0)
    _add_ping(tmp_db, ep.id, None, None, error="timeout")

    csv_output = export_pings_csv(tmp_db)
    lines = csv_output.strip().splitlines()
    assert len(lines) == 4  # header + 3 rows
    assert "https://example.com" in lines[1]
    assert "200" in lines[1]
    assert "123.40" in lines[1]
    assert "timeout" in lines[3]


def test_export_pings_csv_filter_by_url(tmp_db):
    ep1 = add_endpoint(tmp_db, "https://a.com", interval=60)
    ep2 = add_endpoint(tmp_db, "https://b.com", interval=60)
    _add_ping(tmp_db, ep1.id, 200, 50.0)
    _add_ping(tmp_db, ep2.id, 200, 60.0)

    csv_output = export_pings_csv(tmp_db, url="https://a.com")
    lines = csv_output.strip().splitlines()
    assert len(lines) == 2
    assert "https://a.com" in lines[1]
    assert "https://b.com" not in csv_output


def test_export_stats_csv_empty(tmp_db):
    csv_output = export_stats_csv(tmp_db)
    lines = csv_output.strip().splitlines()
    assert len(lines) == 1
    assert "uptime_pct" in lines[0]


def test_export_stats_csv_with_data(tmp_db):
    ep = add_endpoint(tmp_db, "https://stats.com", interval=30)
    _add_ping(tmp_db, ep.id, 200, 100.0)
    _add_ping(tmp_db, ep.id, 200, 200.0)
    _add_ping(tmp_db, ep.id, None, None, error="connection error")

    csv_output = export_stats_csv(tmp_db)
    lines = csv_output.strip().splitlines()
    assert len(lines) == 2
    assert "https://stats.com" in lines[1]
    assert "66.7" in lines[1]  # uptime ~66.7%
    assert "150.00" in lines[1]  # avg latency
