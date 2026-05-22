"""CLI commands for exporting ping data to CSV files."""

import argparse
import sys
from pathlib import Path

from api_pulse.db import db_session
from api_pulse.exporter import export_pings_csv, export_stats_csv


def cmd_export_pings(args: argparse.Namespace) -> None:
    """Export raw ping history to a CSV file."""
    with db_session() as conn:
        csv_data = export_pings_csv(
            conn,
            url=args.url or None,
            limit=args.limit,
        )

    if args.output == "-":
        sys.stdout.write(csv_data)
    else:
        out_path = Path(args.output)
        out_path.write_text(csv_data, encoding="utf-8")
        print(f"Ping history exported to {out_path} ({len(csv_data.splitlines()) - 1} rows).")


def cmd_export_stats(args: argparse.Namespace) -> None:
    """Export aggregated stats for all endpoints to a CSV file."""
    with db_session() as conn:
        csv_data = export_stats_csv(conn)

    if args.output == "-":
        sys.stdout.write(csv_data)
    else:
        out_path = Path(args.output)
        out_path.write_text(csv_data, encoding="utf-8")
        print(f"Stats exported to {out_path} ({len(csv_data.splitlines()) - 1} endpoints).")


def build_export_parser(subparsers) -> None:
    """Register export sub-commands onto an existing subparsers object."""
    # export-pings
    p_pings = subparsers.add_parser(
        "export-pings",
        help="Export raw ping history to CSV.",
    )
    p_pings.add_argument(
        "--url",
        default="",
        help="Filter to a specific endpoint URL (default: all endpoints).",
    )
    p_pings.add_argument(
        "--limit",
        type=int,
        default=500,
        help="Maximum number of pings per endpoint (default: 500).",
    )
    p_pings.add_argument(
        "--output", "-o",
        default="pings.csv",
        help="Output file path, or '-' for stdout (default: pings.csv).",
    )
    p_pings.set_defaults(func=cmd_export_pings)

    # export-stats
    p_stats = subparsers.add_parser(
        "export-stats",
        help="Export aggregated endpoint stats to CSV.",
    )
    p_stats.add_argument(
        "--output", "-o",
        default="stats.csv",
        help="Output file path, or '-' for stdout (default: stats.csv).",
    )
    p_stats.set_defaults(func=cmd_export_stats)
