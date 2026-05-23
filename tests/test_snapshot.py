"""Tests for api_pulse.snapshot."""

import json
import sqlite3
from contextlib import contextmanager

import pytest

from api_pulse.db import init_db
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.models import PingResult
from api_pulse.snapshot import (
    capture_snapshot,
    snapshot_to_json,
    diff_snapshots,
    EndpointSnapshot,
)


@pytest.fixture
def tmp_db():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    init_db(conn)
    yield conn
    conn.close()


def _add_ping(conn, url, success, latency_ms, status_code=200):
    save_ping(conn, PingResult(url=url, success=success,
                               latency_ms=latency_ms, status_code=status_code,
                               error=None))


# --- capture_snapshot ---

def test_capture_snapshot_empty(tmp_db):
    snaps = capture_snapshot(tmp_db)
    assert snaps == []


def test_capture_snapshot_single_endpoint(tmp_db):
    add_endpoint(tmp_db, "https://example.com", 30)
    _add_ping(tmp_db, "https://example.com", True, 42.0)
    _add_ping(tmp_db, "https://example.com", True, 58.0)
    _add_ping(tmp_db, "https://example.com", False, None, status_code=503)

    snaps = capture_snapshot(tmp_db)
    assert len(snaps) == 1
    s = snaps[0]
    assert s.url == "https://example.com"
    assert s.total_pings == 3
    assert s.success_count == 2
    assert s.failure_count == 1
    assert s.avg_latency_ms == pytest.approx(50.0)


def test_capture_snapshot_no_pings(tmp_db):
    add_endpoint(tmp_db, "https://no-pings.io", 60)
    snaps = capture_snapshot(tmp_db)
    assert len(snaps) == 1
    s = snaps[0]
    assert s.total_pings == 0
    assert s.avg_latency_ms is None
    assert s.last_status is None


def test_capture_snapshot_last_status(tmp_db):
    add_endpoint(tmp_db, "https://api.test", 30)
    _add_ping(tmp_db, "https://api.test", True, 10.0, status_code=200)
    _add_ping(tmp_db, "https://api.test", False, None, status_code=500)
    snaps = capture_snapshot(tmp_db)
    # most recent ping is last inserted; repository returns newest first
    assert snaps[0].last_status == 500


# --- snapshot_to_json ---

def test_snapshot_to_json_roundtrip(tmp_db):
    add_endpoint(tmp_db, "https://json.test", 30)
    _add_ping(tmp_db, "https://json.test", True, 20.0)
    snaps = capture_snapshot(tmp_db)
    raw = snapshot_to_json(snaps)
    data = json.loads(raw)
    assert isinstance(data, list)
    assert data[0]["url"] == "https://json.test"
    assert data[0]["success_count"] == 1


# --- diff_snapshots ---

def _snap(url, total, success, avg_lat):
    return EndpointSnapshot(
        url=url, captured_at="2024-01-01T00:00:00",
        total_pings=total, success_count=success,
        failure_count=total - success, avg_latency_ms=avg_lat,
        last_status=200,
    )


def test_diff_no_changes():
    before = [_snap("https://a.io", 10, 10, 30.0)]
    after = [_snap("https://a.io", 10, 10, 30.0)]
    assert diff_snapshots(before, after) == []


def test_diff_detects_new_endpoint():
    before = []
    after = [_snap("https://new.io", 5, 5, 20.0)]
    lines = diff_snapshots(before, after)
    assert any("NEW" in l and "new.io" in l for l in lines)


def test_diff_detects_gone_endpoint():
    before = [_snap("https://gone.io", 5, 5, 20.0)]
    after = []
    lines = diff_snapshots(before, after)
    assert any("GONE" in l and "gone.io" in l for l in lines)


def test_diff_detects_latency_change():
    before = [_snap("https://slow.io", 10, 10, 50.0)]
    after = [_snap("https://slow.io", 20, 20, 200.0)]
    lines = diff_snapshots(before, after)
    assert any("DIFF" in l and "avg_latency" in l for l in lines)


def test_snapshot_str():
    s = _snap("https://x.io", 4, 3, 55.5)
    text = str(s)
    assert "https://x.io" in text
    assert "75.0%" in text
