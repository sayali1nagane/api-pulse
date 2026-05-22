"""Retention policy: prune old ping records from the database."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

from api_pulse.db import db_session


def prune_pings(days: int, url: Optional[str] = None) -> int:
    """Delete ping records older than *days* days.

    If *url* is given only records for that endpoint are removed.
    Returns the number of rows deleted.
    """
    if days < 1:
        raise ValueError("days must be >= 1")

    cutoff: str = (datetime.utcnow() - timedelta(days=days)).isoformat()

    with db_session() as conn:
        if url:
            cursor = conn.execute(
                "DELETE FROM pings WHERE timestamp < ? AND endpoint_url = ?",
                (cutoff, url),
            )
        else:
            cursor = conn.execute(
                "DELETE FROM pings WHERE timestamp < ?",
                (cutoff,),
            )
        deleted: int = cursor.rowcount
    return deleted


def prune_stats() -> dict[str, int]:
    """Return a summary dict with counts per endpoint of remaining pings."""
    with db_session() as conn:
        rows = conn.execute(
            "SELECT endpoint_url, COUNT(*) FROM pings GROUP BY endpoint_url"
        ).fetchall()
    return {row[0]: row[1] for row in rows}
