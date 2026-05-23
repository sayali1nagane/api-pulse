"""Tests for api_pulse.heatmap."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

import pytest

from api_pulse.db import init_db
from api_pulse.heatmap import HeatmapRow, build_heatmap, heatmap_all


@pytest.fixture()
def tmp_db():
    conn = sqlite3.connect(":memory:")
    init_db(conn)
    yield conn
    conn.close()


def _add_ping(conn, url: str, latency_ms: float, success: bool, hour: int, days_ago: int = 0):
    """Insert a synthetic ping at a specific hour on a specific day."""
    ts = datetime.utcnow() - timedelta(days=days_ago)
    ts = ts.replace(hour=hour, minute=0, second=0, microsecond=0)
    conn.execute(
        """
        INSERT INTO pings (endpoint_url, checked_at, latency_ms, status_code, success)
        VALUES (?, ?, ?, ?, ?)
        """,
        (url, ts.strftime("%Y-%m-%d %H:%M:%S"), latency_ms, 200 if success else None, success),
    )
    conn.commit()


URL = "https://example.com/api"


def test_build_heatmap_empty(tmp_db):
    rows = build_heatmap(URL, days=7, conn=tmp_db)
    assert rows == []


def test_build_heatmap_single_bucket(tmp_db):
    _add_ping(tmp_db, URL, 120.0, True, hour=10)
    rows = build_heatmap(URL, days=7, conn=tmp_db)
    assert len(rows) == 1
    r = rows[0]
    assert r.hour == 10
    assert r.sample_count == 1
    assert r.avg_latency_ms == pytest.approx(120.0)
    assert r.min_latency_ms == pytest.approx(120.0)
    assert r.max_latency_ms == pytest.approx(120.0)


def test_build_heatmap_multiple_buckets(tmp_db):
    for latency in (100.0, 200.0, 300.0):
        _add_ping(tmp_db, URL, latency, True, hour=9)
    _add_ping(tmp_db, URL, 50.0, True, hour=14)

    rows = build_heatmap(URL, days=7, conn=tmp_db)
    hours = [r.hour for r in rows]
    assert 9 in hours and 14 in hours

    r9 = next(r for r in rows if r.hour == 9)
    assert r9.sample_count == 3
    assert r9.avg_latency_ms == pytest.approx(200.0)
    assert r9.min_latency_ms == pytest.approx(100.0)
    assert r9.max_latency_ms == pytest.approx(300.0)


def test_build_heatmap_excludes_failures(tmp_db):
    _add_ping(tmp_db, URL, 999.0, False, hour=8)  # failed — should be ignored
    _add_ping(tmp_db, URL, 150.0, True, hour=8)

    rows = build_heatmap(URL, days=7, conn=tmp_db)
    assert len(rows) == 1
    assert rows[0].avg_latency_ms == pytest.approx(150.0)
    assert rows[0].sample_count == 1


def test_build_heatmap_excludes_old_pings(tmp_db):
    _add_ping(tmp_db, URL, 200.0, True, hour=12, days_ago=10)  # older than 7 days
    rows = build_heatmap(URL, days=7, conn=tmp_db)
    assert rows == []


def test_heatmap_row_bar_length():
    row = HeatmapRow(hour=6, sample_count=5, avg_latency_ms=1000.0, min_latency_ms=800.0, max_latency_ms=1200.0)
    bar = row.bar(width=20)
    assert len(bar) == 20
    # 1000ms / 2000ms = 50% → 10 filled blocks
    assert bar.count("█") == 10


def test_heatmap_row_bar_clamps_at_max():
    row = HeatmapRow(hour=0, sample_count=1, avg_latency_ms=5000.0, min_latency_ms=5000.0, max_latency_ms=5000.0)
    bar = row.bar(width=10)
    assert bar == "█" * 10


def test_heatmap_all_multiple_endpoints(tmp_db):
    url2 = "https://other.io/health"
    _add_ping(tmp_db, URL, 100.0, True, hour=9)
    _add_ping(tmp_db, url2, 200.0, True, hour=15)

    result = heatmap_all(days=7, conn=tmp_db)
    assert URL in result and url2 in result
    assert result[URL][0].hour == 9
    assert result[url2][0].hour == 15
