"""Tests for api_pulse.notifier."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest

from api_pulse.alerting import Alert
from api_pulse.notifier import (
    NotifierConfig,
    dispatch,
    notify_console,
    notify_webhook,
)


@pytest.fixture()
def sample_alert() -> Alert:
    return Alert(url="https://example.com/api", failure_rate=0.75, threshold=0.5)


def test_notify_console_writes_to_stderr(sample_alert, capsys):
    notify_console(sample_alert)
    captured = capsys.readouterr()
    assert "ALERT" in captured.err
    assert "example.com" in captured.err


def test_notify_webhook_success(sample_alert):
    config = NotifierConfig(webhook_url="http://hooks.test/notify", console=False)
    mock_response = MagicMock()
    mock_response.__enter__ = lambda s: s
    mock_response.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=mock_response) as mock_open:
        result = notify_webhook(sample_alert, config)

    assert result is True
    args, _ = mock_open.call_args
    req = args[0]
    body = json.loads(req.data)
    assert body["url"] == sample_alert.url
    assert body["failure_rate"] == round(sample_alert.failure_rate, 4)


def test_notify_webhook_no_url_returns_false(sample_alert):
    config = NotifierConfig(webhook_url=None)
    assert notify_webhook(sample_alert, config) is False


def test_notify_webhook_network_error_returns_false(sample_alert):
    import urllib.error
    config = NotifierConfig(webhook_url="http://hooks.test/notify")
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
        result = notify_webhook(sample_alert, config)
    assert result is False


def test_dispatch_console_only(sample_alert, capsys):
    config = NotifierConfig(console=True, webhook_url=None)
    dispatch([sample_alert], config)
    captured = capsys.readouterr()
    assert "ALERT" in captured.err


def test_dispatch_calls_webhook(sample_alert):
    config = NotifierConfig(console=False, webhook_url="http://hooks.test/x")
    with patch("api_pulse.notifier.notify_webhook", return_value=True) as mock_wh:
        dispatch([sample_alert], config)
    mock_wh.assert_called_once_with(sample_alert, config)


def test_dispatch_empty_alerts():
    config = NotifierConfig(console=True)
    with patch("api_pulse.notifier.notify_console") as mock_c:
        dispatch([], config)
    mock_c.assert_not_called()
