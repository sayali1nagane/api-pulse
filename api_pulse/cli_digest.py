"""CLI commands for the periodic digest feature."""

from __future__ import annotations

import argparse
import sys

from .db import db_session
from .digest import build_digest


def cmd_digest(args: argparse.Namespace) -> None:
    """Print a digest report to stdout."""
    window = args.hours
    if window <= 0:
        print("error: --hours must be a positive integer", file=sys.stderr)
        sys.exit(1)

    with db_session() as conn:
        digest = build_digest(conn, window_hours=window, limit=args.limit)

    if args.json:
        import json
        from dataclasses import asdict

        def _serialise(obj):
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            raise TypeError(type(obj))

        rows = [
            {
                "url": e.url,
                "total": e.total,
                "successes": e.successes,
                "success_rate": round(e.success_rate, 2),
                "avg_latency_ms": e.avg_latency_ms,
                "min_latency_ms": e.min_latency_ms,
                "max_latency_ms": e.max_latency_ms,
            }
            for e in digest.entries
        ]
        payload = {
            "generated_at": digest.generated_at.isoformat(),
            "window_hours": digest.window_hours,
            "entries": rows,
        }
        print(json.dumps(payload, indent=2, default=_serialise))
    else:
        print(str(digest))


def build_digest_parser(subparsers) -> argparse.ArgumentParser:
    p = subparsers.add_parser(
        "digest",
        help="Show a periodic digest of recent ping activity",
    )
    p.add_argument(
        "--hours",
        type=int,
        default=24,
        metavar="N",
        help="Summarise pings from the last N hours (default: 24)",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=500,
        metavar="N",
        help="Maximum pings to fetch per endpoint (default: 500)",
    )
    p.add_argument(
        "--json",
        action="store_true",
        default=False,
        help="Output as JSON instead of plain text",
    )
    p.set_defaults(func=cmd_digest)
    return p
