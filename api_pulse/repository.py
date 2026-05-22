from typing import List, Optional
from api_pulse.db import db_session
from api_pulse.models import Endpoint, PingResult


def add_endpoint(name: str, url: str, db_path: str = None) -> Endpoint:
    kwargs = {"db_path": db_path} if db_path else {}
    with db_session(**kwargs) as conn:
        cursor = conn.execute(
            "INSERT INTO endpoints (name, url) VALUES (?, ?)", (name, url)
        )
        row = conn.execute(
            "SELECT * FROM endpoints WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return Endpoint.from_row(row)


def list_endpoints(db_path: str = None) -> List[Endpoint]:
    kwargs = {"db_path": db_path} if db_path else {}
    with db_session(**kwargs) as conn:
        rows = conn.execute("SELECT * FROM endpoints ORDER BY name").fetchall()
        return [Endpoint.from_row(r) for r in rows]


def get_endpoint_by_url(url: str, db_path: str = None) -> Optional[Endpoint]:
    kwargs = {"db_path": db_path} if db_path else {}
    with db_session(**kwargs) as conn:
        row = conn.execute(
            "SELECT * FROM endpoints WHERE url = ?", (url,)
        ).fetchone()
        return Endpoint.from_row(row) if row else None


def save_ping(result: PingResult, db_path: str = None) -> PingResult:
    kwargs = {"db_path": db_path} if db_path else {}
    with db_session(**kwargs) as conn:
        cursor = conn.execute(
            """INSERT INTO pings (endpoint_id, status_code, latency_ms, success, error)
               VALUES (?, ?, ?, ?, ?)""",
            (result.endpoint_id, result.status_code, result.latency_ms,
             int(result.success), result.error),
        )
        row = conn.execute(
            "SELECT * FROM pings WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return PingResult.from_row(row)


def get_recent_pings(endpoint_id: int, limit: int = 20, db_path: str = None) -> List[PingResult]:
    kwargs = {"db_path": db_path} if db_path else {}
    with db_session(**kwargs) as conn:
        rows = conn.execute(
            """SELECT * FROM pings WHERE endpoint_id = ?
               ORDER BY pinged_at DESC LIMIT ?""",
            (endpoint_id, limit),
        ).fetchall()
        return [PingResult.from_row(r) for r in rows]
