import os
import tempfile
import pytest
from api_pulse.db import init_db
from api_pulse.repository import (
    add_endpoint,
    list_endpoints,
    get_endpoint_by_url,
    save_ping,
    get_recent_pings,
)
from api_pulse.models import PingResult


@pytest.fixture
def tmp_db():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    init_db(db_path)
    yield db_path
    os.unlink(db_path)


def test_add_and_list_endpoints(tmp_db):
    ep = add_endpoint("HTTPBin", "https://httpbin.org/get", db_path=tmp_db)
    assert ep.id is not None
    assert ep.name == "HTTPBin"
    assert ep.url == "https://httpbin.org/get"

    endpoints = list_endpoints(db_path=tmp_db)
    assert len(endpoints) == 1
    assert endpoints[0].url == "https://httpbin.org/get"


def test_get_endpoint_by_url(tmp_db):
    add_endpoint("Google", "https://google.com", db_path=tmp_db)
    ep = get_endpoint_by_url("https://google.com", db_path=tmp_db)
    assert ep is not None
    assert ep.name == "Google"

    missing = get_endpoint_by_url("https://notexist.example", db_path=tmp_db)
    assert missing is None


def test_save_and_retrieve_pings(tmp_db):
    ep = add_endpoint("API", "https://api.example.com", db_path=tmp_db)

    result = PingResult(endpoint_id=ep.id, success=True, latency_ms=42.5, status_code=200)
    saved = save_ping(result, db_path=tmp_db)
    assert saved.id is not None
    assert saved.latency_ms == 42.5
    assert saved.success is True

    pings = get_recent_pings(ep.id, db_path=tmp_db)
    assert len(pings) == 1
    assert pings[0].status_code == 200


def test_failed_ping_saved(tmp_db):
    ep = add_endpoint("Broken", "https://broken.example.com", db_path=tmp_db)
    result = PingResult(endpoint_id=ep.id, success=False, error="Connection refused")
    saved = save_ping(result, db_path=tmp_db)
    assert saved.success is False
    assert saved.error == "Connection refused"
    assert str(saved) == "FAIL — Connection refused"


def test_get_recent_pings_limit(tmp_db):
    ep = add_endpoint("LimitTest", "https://limit.example.com", db_path=tmp_db)
    for i in range(5):
        save_ping(PingResult(endpoint_id=ep.id, success=True, latency_ms=float(i)), db_path=tmp_db)

    pings = get_recent_pings(ep.id, limit=3, db_path=tmp_db)
    assert len(pings) == 3
