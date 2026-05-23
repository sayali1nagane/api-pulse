"""Main CLI entry-point for api-pulse."""

from __future__ import annotations

import argparse
import sys

from .db import init_db, db_session
from .cli import cmd_add, cmd_list, cmd_report, cmd_start
from .cli_export import build_export_parser
from .cli_alert import build_alert_parser
from .cli_notify import build_notify_parser
from .cli_history import build_history_parser
from .cli_summary import build_summary_parser
from .cli_retention import build_retention_parser
from .cli_anomaly import build_anomaly_parser
from .cli_digest import build_digest_parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="api-pulse",
        description="Minimal uptime monitor for REST endpoints",
    )
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    # core commands
    add_p = sub.add_parser("add", help="Register a new endpoint")
    add_p.add_argument("url")
    add_p.add_argument("--name", default="")
    add_p.set_defaults(func=cmd_add)

    list_p = sub.add_parser("list", help="List registered endpoints")
    list_p.set_defaults(func=cmd_list)

    report_p = sub.add_parser("report", help="Show latency report")
    report_p.add_argument("--url", default=None)
    report_p.set_defaults(func=cmd_report)

    start_p = sub.add_parser("start", help="Start the scheduler")
    start_p.add_argument("--interval", type=int, default=60)
    start_p.set_defaults(func=cmd_start)

    # feature sub-parsers
    build_export_parser(sub)
    build_alert_parser(sub)
    build_notify_parser(sub)
    build_history_parser(sub)
    build_summary_parser(sub)
    build_retention_parser(sub)
    build_anomaly_parser(sub)
    build_digest_parser(sub)

    return parser


def main(argv=None) -> None:  # pragma: no cover
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    with db_session() as conn:
        init_db(conn)

    args.func(args)
