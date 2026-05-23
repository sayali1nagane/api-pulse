"""Tests for api_pulse.cli_anomaly."""

from __future__ import annotations

import argparse
import pytest

from unittest.mock import patch, MagicMock
from api_pulse.cli_anomaly import cmd_scan_anomalies, build_anomaly_parser
from api_pulse.anomaly import Anomaly


def _make_args(**kwargs):
    defaults = {"sigma": 2.0, "lookback": 60, "fail_on_anomaly": False}
    defaults.update(kwargs)
    return argparse.Namespace(**defaults)


@patch("api_pulse.cli_anomaly.db_session")
@patch("api_pulse.cli_anomaly.scan_anomalies", return_value=[])
def test_no_anomalies_prints_ok(mock_scan, mock_session, capsys):
    mock_session.return_value.__enter__ = lambda s, *a: MagicMock()
    mock_session.return_value.__exit__ = lambda s, *a: False
    cmd_scan_anomalies(_make_args())
    out = capsys.readouterr().out
    assert "No anomalies" in out


@patch("api_pulse.cli_anomaly.db_session")
@patch("api_pulse.cli_anomaly.scan_anomalies")
def test_anomalies_printed(mock_scan, mock_session, capsys):
    mock_session.return_value.__enter__ = lambda s, *a: MagicMock()
    mock_session.return_value.__exit__ = lambda s, *a: False
    mock_scan.return_value = [
        Anomaly(url="http://x.test", latency_ms=500.0, baseline_avg_ms=100.0, baseline_std_ms=20.0, sigma=20.0)
    ]
    cmd_scan_anomalies(_make_args())
    out = capsys.readouterr().out
    assert "1 anomaly" in out
    assert "http://x.test" in out


@patch("api_pulse.cli_anomaly.db_session")
@patch("api_pulse.cli_anomaly.scan_anomalies")
def test_fail_on_anomaly_exits(mock_scan, mock_session):
    mock_session.return_value.__enter__ = lambda s, *a: MagicMock()
    mock_session.return_value.__exit__ = lambda s, *a: False
    mock_scan.return_value = [
        Anomaly(url="http://x.test", latency_ms=500.0, baseline_avg_ms=100.0, baseline_std_ms=20.0, sigma=20.0)
    ]
    with pytest.raises(SystemExit) as exc_info:
        cmd_scan_anomalies(_make_args(fail_on_anomaly=True))
    assert exc_info.value.code == 1


def test_build_anomaly_parser_registers_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    build_anomaly_parser(sub)
    args = parser.parse_args(["scan-anomalies", "--sigma", "3.0", "--lookback", "30"])
    assert args.sigma == 3.0
    assert args.lookback == 30
    assert args.fail_on_anomaly is False
