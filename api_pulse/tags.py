"""Tag management for endpoints — assign, remove, and filter endpoints by tag."""

from __future__ import annotations

import sqlite3
from typing import List


def add_tag(conn: sqlite3.Connection, url: str, tag: str) -> None:
    """Associate a tag with an endpoint URL. Silently ignores duplicates."""
    conn.execute(
        """
        INSERT OR IGNORE INTO endpoint_tags (url, tag)
        VALUES (?, ?)
        """,
        (url, tag.strip().lower()),
    )
    conn.commit()


def remove_tag(conn: sqlite3.Connection, url: str, tag: str) -> None:
    """Remove a tag from an endpoint URL."""
    conn.execute(
        "DELETE FROM endpoint_tags WHERE url = ? AND tag = ?",
        (url, tag.strip().lower()),
    )
    conn.commit()


def list_tags(conn: sqlite3.Connection, url: str) -> List[str]:
    """Return all tags associated with a given endpoint URL."""
    rows = conn.execute(
        "SELECT tag FROM endpoint_tags WHERE url = ? ORDER BY tag",
        (url,),
    ).fetchall()
    return [row[0] for row in rows]


def endpoints_by_tag(conn: sqlite3.Connection, tag: str) -> List[str]:
    """Return all endpoint URLs that carry the given tag."""
    rows = conn.execute(
        "SELECT url FROM endpoint_tags WHERE tag = ? ORDER BY url",
        (tag.strip().lower(),),
    ).fetchall()
    return [row[0] for row in rows]


def ensure_tags_table(conn: sqlite3.Connection) -> None:
    """Create the endpoint_tags table if it does not already exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS endpoint_tags (
            url  TEXT NOT NULL,
            tag  TEXT NOT NULL,
            PRIMARY KEY (url, tag)
        )
        """
    )
    conn.commit()
