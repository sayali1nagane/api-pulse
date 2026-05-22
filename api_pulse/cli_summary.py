"""CLI sub-commands for the summary feature."""

from __future__ import annotations

import argparse
import sys

from api_pulse.db import db_session
from api_pulse.summarizer import summarize_all, summarize_endpoint


def cmd_summary(args: argparse.Namespace) -> None:
    """Print a summary report to stdout."""
    period: int = args.hours
    url: str | None = getattr(args, "url", None)

    with db_session() as conn:
        if url:
            entry = summarize_endpoint(conn, url, period_hours=period)
            if entry is None:
                print(f"No data for '{url}' in the last {period} hours.", file=sys.stderr)
                sys.exit(1)
            entries = [entry]
        else:
            entries = summarize_all(conn, period_hours=period)

    if not entries:
        print(f"No ping data available for the last {period} hours.")
        return

    print(f"=== Summary (last {period}h) ===")
    for e in entries:
        print(str(e))


def build_summary_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    """Register the 'summary' sub-command."""
    p = subparsers.add_parser(
        "summary",
        help="Show an uptime/latency summary for monitored endpoints",
    )
    p.add_argument(
        "--hours",
        type=int,
        default=24,
        metavar="N",
        help="Look-back window in hours (default: 24)",
    )
    p.add_argument(
        "--url",
        metavar="URL",
        default=None,
        help="Restrict summary to a single endpoint URL",
    )
    p.set_defaults(func=cmd_summary)
