"""Tests for api_pulse.cli_digest."""

from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from api_pulse.cli_digest import cmd_digest, build_digest_parser
from api_pulse.digest import Digest, DigestEntry


def _make_args(**kwargs):
    defaults = {"hours": 24, "limit": 500, "json": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def _fake_digest(entries=None):
    return Digest(
        generated_at=datetime(2024, 1, 1, 12, 0, 0),
        window_hours=24,
        entries=entries or [],
    )


def test_cmd_digest_plain_output(capsys):
    digest = _fake_digest([
        DigestEntry(
            url="https://example.com", total=10, successes=9,
            avg_latency_ms=150.0, min_latency_ms=100.0, max_latency_ms=200.0,
            window_hours=24,
        )
    ])
    with patch("api_pulse.cli_digest.db_session") as mock_sess, \
         patch("api_pulse.cli_digest.build_digest", return_value=digest):
        mock_sess.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_sess.return_value.__exit__ = MagicMock(return_value=False)
        cmd_digest(_make_args())

    out = capsys.readouterr().out
    assert "https://example.com" in out
    assert "success=90.0%" in out


def test_cmd_digest_json_output(capsys):
    digest = _fake_digest([
        DigestEntry(
            url="https://api.io", total=5, successes=5,
            avg_latency_ms=80.0, min_latency_ms=70.0, max_latency_ms=90.0,
            window_hours=24,
        )
    ])
    with patch("api_pulse.cli_digest.db_session") as mock_sess, \
         patch("api_pulse.cli_digest.build_digest", return_value=digest):
        mock_sess.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_sess.return_value.__exit__ = MagicMock(return_value=False)
        cmd_digest(_make_args(json=True))

    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["window_hours"] == 24
    assert len(data["entries"]) == 1
    assert data["entries"][0]["url"] == "https://api.io"
    assert data["entries"][0]["success_rate"] == 100.0


def test_cmd_digest_invalid_hours_exits():
    with pytest.raises(SystemExit):
        cmd_digest(_make_args(hours=0))


def test_build_digest_parser_registers_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    build_digest_parser(sub)
    args = parser.parse_args(["digest", "--hours", "6", "--json"])
    assert args.hours == 6
    assert args.json is True
    assert args.limit == 500
