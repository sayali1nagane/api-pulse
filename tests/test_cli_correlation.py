"""Tests for api_pulse.cli_correlation."""
from __future__ import annotations

import argparse
import sqlite3
import time
from unittest.mock import patch, MagicMock

import pytest

from api_pulse.db import init_db
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.models import PingResult
from api_pulse.cli_correlation import cmd_correlate, build_correlation_parser
from api_pulse.correlation import CorrelationResult


def _make_args(**kwargs):
    defaults = dict(url_a=None, url_b=None, limit=60, fail_on_strong=False)
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _fake_session(results):
    """Context manager mock that returns a fake connection yielding given results."""
    conn = MagicMock()
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=conn)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx, conn


def test_cmd_correlate_all_no_results(capsys):
    ctx, conn = _fake_session([])
    with patch("api_pulse.cli_correlation.db_session", return_value=ctx), \
         patch("api_pulse.cli_correlation.correlate_all", return_value=[]):
        cmd_correlate(_make_args())
    out = capsys.readouterr().out
    assert "Not enough" in out


def test_cmd_correlate_all_prints_results(capsys):
    r = CorrelationResult("http://a", "http://b", 0.95, 10)
    ctx, conn = _fake_session([r])
    with patch("api_pulse.cli_correlation.db_session", return_value=ctx), \
         patch("api_pulse.cli_correlation.correlate_all", return_value=[r]):
        cmd_correlate(_make_args())
    out = capsys.readouterr().out
    assert "http://a" in out
    assert "http://b" in out


def test_cmd_correlate_fail_on_strong_exits(capsys):
    r = CorrelationResult("http://a", "http://b", 0.95, 10)
    ctx, conn = _fake_session([r])
    with patch("api_pulse.cli_correlation.db_session", return_value=ctx), \
         patch("api_pulse.cli_correlation.correlate_all", return_value=[r]):
        with pytest.raises(SystemExit) as exc:
            cmd_correlate(_make_args(fail_on_strong=True))
    assert exc.value.code == 1


def test_cmd_correlate_pair_insufficient_data(capsys):
    r = CorrelationResult("http://a", "http://b", None, 1)
    ctx, conn = _fake_session(r)
    with patch("api_pulse.cli_correlation.db_session", return_value=ctx), \
         patch("api_pulse.cli_correlation.correlate_endpoints", return_value=r):
        with pytest.raises(SystemExit) as exc:
            cmd_correlate(_make_args(url_a="http://a", url_b="http://b"))
    assert exc.value.code == 2


def test_build_correlation_parser_registers_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    build_correlation_parser(sub)
    args = parser.parse_args(["correlate", "--limit", "30"])
    assert args.limit == 30
    assert args.func is cmd_correlate
