"""Tests for api_pulse.alerting."""

import pytest
from api_pulse.db import get_connection, init_db
from api_pulse.repository import add_endpoint, save_ping
from api_pulse.alerting import AlertRule, check_endpoint, run_alerts


@pytest.fixture
def tmp_db(tmp_path):
    db_file = tmp_path / "test.db"
    conn = get_connection(str(db_file))
    init_db(conn)
    yield conn
    conn.close()


def _add_pings(conn, url: str, successes: list[bool]):
    for ok in successes:
        save_ping(conn, url, latency_ms=50.0 if ok else None, success=ok)


# ---------------------------------------------------------------------------

def test_no_alert_when_too_few_pings(tmp_db):
    add_endpoint(tmp_db, "https://api.example.com", interval=60)
    _add_pings(tmp_db, "https://api.example.com", [False, False])  # only 2
    rule = AlertRule(min_pings=3)
    alert = check_endpoint("https://api.example.com", tmp_db, rule)
    assert alert is None


def test_no_alert_when_low_failure_rate(tmp_db):
    add_endpoint(tmp_db, "https://api.example.com", interval=60)
    _add_pings(tmp_db, "https://api.example.com", [True, True, True, False])
    rule = AlertRule(failure_rate_threshold=0.5, min_pings=3)
    alert = check_endpoint("https://api.example.com", tmp_db, rule)
    assert alert is None


def test_alert_triggered_on_high_failure_rate(tmp_db):
    add_endpoint(tmp_db, "https://bad.example.com", interval=60)
    _add_pings(tmp_db, "https://bad.example.com", [False, False, False, True])
    rule = AlertRule(failure_rate_threshold=0.5, min_pings=3)
    alert = check_endpoint("https://bad.example.com", tmp_db, rule)
    assert alert is not None
    assert alert.url == "https://bad.example.com"
    assert alert.failure_rate == pytest.approx(0.75)
    assert alert.total_checked == 4


def test_alert_exact_threshold_triggers(tmp_db):
    add_endpoint(tmp_db, "https://edge.example.com", interval=60)
    _add_pings(tmp_db, "https://edge.example.com", [False, False, True, True])
    rule = AlertRule(failure_rate_threshold=0.5, min_pings=3)
    alert = check_endpoint("https://edge.example.com", tmp_db, rule)
    assert alert is not None
    assert alert.failure_rate == pytest.approx(0.5)


def test_run_alerts_multiple_endpoints(tmp_db):
    add_endpoint(tmp_db, "https://ok.example.com", interval=60)
    add_endpoint(tmp_db, "https://fail.example.com", interval=60)
    _add_pings(tmp_db, "https://ok.example.com", [True, True, True])
    _add_pings(tmp_db, "https://fail.example.com", [False, False, False])
    rule = AlertRule(failure_rate_threshold=0.5, min_pings=3)
    alerts = run_alerts(tmp_db, rule)
    assert len(alerts) == 1
    assert alerts[0].url == "https://fail.example.com"


def test_run_alerts_empty_db(tmp_db):
    alerts = run_alerts(tmp_db)
    assert alerts == []


def test_run_alerts_respects_window(tmp_db):
    """Only the last `window` pings are considered."""
    add_endpoint(tmp_db, "https://recover.example.com", interval=60)
    # Old failures, then recent successes
    _add_pings(tmp_db, "https://recover.example.com",
               [False, False, False, False, False,
                True, True, True, True, True])
    rule = AlertRule(failure_rate_threshold=0.5, min_pings=3, window=5)
    alert = check_endpoint("https://recover.example.com", tmp_db, rule)
    # window=5 picks the 5 most recent pings; repository returns newest first
    assert alert is None
