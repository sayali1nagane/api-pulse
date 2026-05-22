import pytest
from unittest.mock import patch, MagicMock

from api_pulse.models import Endpoint
from api_pulse.pinger import ping_endpoint, ping_all


def make_endpoint(url: str = "https://example.com/health") -> Endpoint:
    return Endpoint(id=1, url=url, name="Test", interval_seconds=60)


def test_ping_success():
    endpoint = make_endpoint()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True

    with patch("api_pulse.pinger.requests.get", return_value=mock_response):
        result = ping_endpoint(endpoint)

    assert result.success is True
    assert result.status_code == 200
    assert result.error is None
    assert result.latency_ms >= 0
    assert result.endpoint_id == endpoint.id


def test_ping_non_ok_status():
    endpoint = make_endpoint()
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_response.ok = False

    with patch("api_pulse.pinger.requests.get", return_value=mock_response):
        result = ping_endpoint(endpoint)

    assert result.success is False
    assert result.status_code == 503
    assert result.error is None


def test_ping_timeout():
    import requests as req
    endpoint = make_endpoint()

    with patch("api_pulse.pinger.requests.get", side_effect=req.exceptions.Timeout):
        result = ping_endpoint(endpoint)

    assert result.success is False
    assert result.status_code is None
    assert "timed out" in result.error


def test_ping_connection_error():
    import requests as req
    endpoint = make_endpoint()

    with patch("api_pulse.pinger.requests.get", side_effect=req.exceptions.ConnectionError("refused")):
        result = ping_endpoint(endpoint)

    assert result.success is False
    assert result.status_code is None
    assert "Connection error" in result.error


def test_ping_all_returns_results_for_each_endpoint():
    endpoints = [make_endpoint(f"https://example.com/ep{i}") for i in range(3)]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.ok = True

    with patch("api_pulse.pinger.requests.get", return_value=mock_response):
        results = ping_all(endpoints)

    assert len(results) == 3
    assert all(r.success for r in results)
