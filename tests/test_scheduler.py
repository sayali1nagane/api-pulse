import time
import pytest
from unittest.mock import patch, MagicMock

from api_pulse.scheduler import PingScheduler
from api_pulse.models import Endpoint


def make_endpoint(url: str = "https://example.com/health") -> Endpoint:
    return Endpoint(id=1, url=url, name="Example", interval_seconds=60)


@patch("api_pulse.scheduler.ping_all")
@patch("api_pulse.scheduler.list_endpoints")
@patch("api_pulse.scheduler.db_session")
def test_scheduler_calls_ping_all(mock_db_session, mock_list, mock_ping_all):
    """Scheduler should call ping_all with listed endpoints."""
    endpoint = make_endpoint()
    mock_list.return_value = [endpoint]
    mock_db_session.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

    scheduler = PingScheduler(interval_seconds=1)
    scheduler.start()
    time.sleep(0.3)
    scheduler.stop(timeout=2)

    mock_ping_all.assert_called()
    called_endpoints = mock_ping_all.call_args[0][0]
    assert called_endpoints == [endpoint]


@patch("api_pulse.scheduler.ping_all")
@patch("api_pulse.scheduler.list_endpoints")
@patch("api_pulse.scheduler.db_session")
def test_scheduler_skips_when_no_endpoints(mock_db_session, mock_list, mock_ping_all):
    """Scheduler should not call ping_all when no endpoints are registered."""
    mock_list.return_value = []
    mock_db_session.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

    scheduler = PingScheduler(interval_seconds=1)
    scheduler.start()
    time.sleep(0.3)
    scheduler.stop(timeout=2)

    mock_ping_all.assert_not_called()


@patch("api_pulse.scheduler.ping_all")
@patch("api_pulse.scheduler.list_endpoints")
@patch("api_pulse.scheduler.db_session")
def test_scheduler_continues_after_error(mock_db_session, mock_list, mock_ping_all):
    """Scheduler should keep running even if a ping cycle raises an exception."""
    mock_list.side_effect = [Exception("DB error"), [make_endpoint()]]
    mock_db_session.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

    scheduler = PingScheduler(interval_seconds=1)
    scheduler.start()
    time.sleep(1.5)
    scheduler.stop(timeout=2)

    assert mock_ping_all.call_count >= 1


def test_start_stop_lifecycle():
    """Scheduler should correctly report running state."""
    with patch("api_pulse.scheduler.db_session") as mock_db_session, \
         patch("api_pulse.scheduler.list_endpoints", return_value=[]), \
         patch("api_pulse.scheduler.ping_all"):
        mock_db_session.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_db_session.return_value.__exit__ = MagicMock(return_value=False)

        scheduler = PingScheduler(interval_seconds=60)
        assert not scheduler.is_running
        scheduler.start()
        assert scheduler.is_running
        scheduler.stop(timeout=2)
        assert not scheduler.is_running
