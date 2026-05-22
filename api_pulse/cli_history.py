"""CLI sub-commands for latency history and sparkline display."""

from __future__ import annotations

import argparse
import sys

from api_pulse.db import db_session
from api_pulse.history import fetch_history
from api_pulse.repository import list_endpoints


def cmd_history(args: argparse.Namespace) -> None:
    """Show latency sparkline history for one or all endpoints."""
    with db_session() as conn:
        if args.url:
            urls = [args.url]
        else:
            endpoints = list_endpoints(conn)
            if not endpoints:
                print("No endpoints registered.", file=sys.stderr)
                return
            urls = [e.url for e in endpoints]

        window = args.window
        found_any = False
        for url in urls:
            hist = fetch_history(conn, url, window=window)
            if hist.available == 0 and args.url:
                print(f"No ping data found for {url}", file=sys.stderr)
            else:
                print(hist)
                found_any = True

        if not found_any and not args.url:
            print("No ping data recorded yet.", file=sys.stderr)


def build_history_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "history",
        help="Show latency sparkline and statistics for endpoints",
    )
    p.add_argument(
        "--url",
        metavar="URL",
        default=None,
        help="Show history for a specific endpoint URL only",
    )
    p.add_argument(
        "--window",
        metavar="N",
        type=int,
        default=20,
        help="Number of recent pings to include (default: 20)",
    )
    p.set_defaults(func=cmd_history)
