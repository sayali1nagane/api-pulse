"""Tests for api_pulse.cli_retention CLI commands."""

from __future__ import annotations

import argparse
import sys
from unittest.mock import MagicMock, patch

import pytest

from api_pulse.cli_retention import build_retention_parser, cmd_prune, cmd_retention_stats


def _make_args(**kwargs: object) -> argparse.Namespace:
    defaults = {"days": 30, "url": ""}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


def test_cmd_prune_prints_deleted_count(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("api_pulse.cli_retention.prune_pings", return_value=5) as mock_prune:
        cmd_prune(_make_args(days=30, url=""))
        mock_prune.assert_called_once_with(days=30, url=None)
    out = capsys.readouterr().out
    assert "5" in out
    assert "30" in out


def test_cmd_prune_with_url(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("api_pulse.cli_retention.prune_pings", return_value=2):
        cmd_prune(_make_args(days=7, url="https://example.com"))
    out = capsys.readouterr().out
    assert "https://example.com" in out


def test_cmd_prune_invalid_days_exits(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("api_pulse.cli_retention.prune_pings", side_effect=ValueError("days must be >= 1")):
        with pytest.raises(SystemExit):
            cmd_prune(_make_args(days=0))
    err = capsys.readouterr().err
    assert "Error" in err


def test_cmd_retention_stats_empty(capsys: pytest.CaptureFixture[str]) -> None:
    with patch("api_pulse.cli_retention.prune_stats", return_value={}):
        cmd_retention_stats(argparse.Namespace())
    out = capsys.readouterr().out
    assert "No ping records" in out


def test_cmd_retention_stats_with_data(capsys: pytest.CaptureFixture[str]) -> None:
    with patch(
        "api_pulse.cli_retention.prune_stats",
        return_value={"https://a.example.com": 42},
    ):
        cmd_retention_stats(argparse.Namespace())
    out = capsys.readouterr().out
    assert "https://a.example.com" in out
    assert "42" in out


def test_build_retention_parser_registers_subcommands() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    build_retention_parser(sub)
    args = parser.parse_args(["prune", "--days", "14"])
    assert args.days == 14
    assert args.func is cmd_prune
