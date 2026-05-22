"""Integration tests for the `report` CLI command."""

import sqlite3
import pytest
from unittest.mock import patch
from api_pulse.db import init_db
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.cli import build_parser, cmd_report


@pytest.fixture
def tmp_conn(tmp_path):
    db_file = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row
    init_db(conn)
    return conn


def run_report(conn, extra_args=None):
    """Helper: parse report args and invoke cmd_report with a patched db_session."""
    parser = build_parser()
    argv = ["report"] + (extra_args or [])
    args = parser.parse_args(argv)

    from contextlib import contextmanager

    @contextmanager
    def fake_session():
        yield conn

    with patch("api_pulse.cli.db_session", fake_session):
        cmd_report(args)


def test_report_no_endpoints(tmp_conn, capsys):
    run_report(tmp_conn)
    out = capsys.readouterr().out
    assert "No endpoints" in out


def test_report_all_endpoints(tmp_conn, capsys):
    add_endpoint(tmp_conn, "https://x.com", "x")
    add_endpoint(tmp_conn, "https://y.com", "y")
    save_ping(tmp_conn, "https://x.com", success=True, latency_ms=42.0, status_code=200)
    save_ping(tmp_conn, "https://y.com", success=False, latency_ms=None, status_code=500)

    run_report(tmp_conn)
    out = capsys.readouterr().out
    assert "https://x.com" in out
    assert "https://y.com" in out
    assert "uptime=100.0%" in out
    assert "uptime=0.0%" in out


def test_report_single_url(tmp_conn, capsys):
    add_endpoint(tmp_conn, "https://only.com", "only")
    save_ping(tmp_conn, "https://only.com", success=True, latency_ms=77.0, status_code=200)

    run_report(tmp_conn, extra_args=["--url", "https://only.com"])
    out = capsys.readouterr().out
    assert "https://only.com" in out
    assert "avg=77.0ms" in out


def test_report_unknown_url_exits(tmp_conn):
    parser = build_parser()
    args = parser.parse_args(["report", "--url", "https://ghost.com"])

    from contextlib import contextmanager

    @contextmanager
    def fake_session():
        yield tmp_conn

    with patch("api_pulse.cli.db_session", fake_session):
        with pytest.raises(SystemExit) as exc_info:
            cmd_report(args)
    assert exc_info.value.code == 1


def test_report_limit_flag(tmp_conn, capsys):
    add_endpoint(tmp_conn, "https://limited.com", "limited")
    for i in range(10):
        save_ping(tmp_conn, "https://limited.com", success=True, latency_ms=float(i * 10), status_code=200)

    run_report(tmp_conn, extra_args=["--limit", "5"])
    out = capsys.readouterr().out
    assert "https://limited.com" in out
