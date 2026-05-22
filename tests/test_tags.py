"""Tests for api_pulse.tags — endpoint tagging feature."""

import sqlite3
import pytest

from api_pulse.tags import (
    add_tag,
    remove_tag,
    list_tags,
    endpoints_by_tag,
    ensure_tags_table,
)


@pytest.fixture()
def tmp_conn():
    """In-memory SQLite connection with the tags table initialised."""
    conn = sqlite3.connect(":memory:")
    ensure_tags_table(conn)
    yield conn
    conn.close()


def test_add_and_list_tags(tmp_conn):
    add_tag(tmp_conn, "https://example.com", "production")
    add_tag(tmp_conn, "https://example.com", "critical")
    tags = list_tags(tmp_conn, "https://example.com")
    assert sorted(tags) == ["critical", "production"]


def test_add_tag_normalises_case(tmp_conn):
    add_tag(tmp_conn, "https://example.com", "  Production  ")
    tags = list_tags(tmp_conn, "https://example.com")
    assert tags == ["production"]


def test_add_duplicate_tag_is_idempotent(tmp_conn):
    add_tag(tmp_conn, "https://example.com", "staging")
    add_tag(tmp_conn, "https://example.com", "staging")  # duplicate
    tags = list_tags(tmp_conn, "https://example.com")
    assert tags.count("staging") == 1


def test_remove_tag(tmp_conn):
    add_tag(tmp_conn, "https://example.com", "staging")
    add_tag(tmp_conn, "https://example.com", "production")
    remove_tag(tmp_conn, "https://example.com", "staging")
    tags = list_tags(tmp_conn, "https://example.com")
    assert tags == ["production"]


def test_remove_nonexistent_tag_is_safe(tmp_conn):
    # Should not raise even if the tag does not exist
    remove_tag(tmp_conn, "https://example.com", "ghost")
    assert list_tags(tmp_conn, "https://example.com") == []


def test_endpoints_by_tag(tmp_conn):
    add_tag(tmp_conn, "https://alpha.io", "production")
    add_tag(tmp_conn, "https://beta.io", "production")
    add_tag(tmp_conn, "https://gamma.io", "staging")
    urls = endpoints_by_tag(tmp_conn, "production")
    assert sorted(urls) == ["https://alpha.io", "https://beta.io"]


def test_endpoints_by_tag_empty(tmp_conn):
    urls = endpoints_by_tag(tmp_conn, "nonexistent")
    assert urls == []


def test_list_tags_unknown_url_returns_empty(tmp_conn):
    assert list_tags(tmp_conn, "https://unknown.io") == []
