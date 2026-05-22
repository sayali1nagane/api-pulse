"""Unified entry-point that wires all sub-command groups together."""

from __future__ import annotations

import argparse
import sys

from api_pulse.cli import cmd_add, cmd_list, cmd_report, cmd_start
from api_pulse.cli_export import build_export_parser
from api_pulse.cli_alert import build_alert_parser
from api_pulse.cli_notify import build_notify_parser
from api_pulse.cli_history import build_history_parser
from api_pulse.cli_summary import build_summary_parser
from api_pulse.cli_retention import build_retention_parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="api-pulse",
        description="Minimal uptime monitor for REST endpoints.",
    )
    sub = parser.add_subparsers(dest="command")

    # Core commands
    p_add = sub.add_parser("add", help="Register a new endpoint")
    p_add.add_argument("url", help="Endpoint URL")
    p_add.add_argument("--name", default="", help="Human-readable name")
    p_add.add_argument("--interval", type=int, default=60)
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List registered endpoints")
    p_list.set_defaults(func=cmd_list)

    p_report = sub.add_parser("report", help="Show latency report")
    p_report.add_argument("--url", default="")
    p_report.set_defaults(func=cmd_report)

    p_start = sub.add_parser("start", help="Start the scheduler")
    p_start.add_argument("--interval", type=int, default=60)
    p_start.set_defaults(func=cmd_start)

    # Feature sub-command groups
    build_export_parser(sub)
    build_alert_parser(sub)
    build_notify_parser(sub)
    build_history_parser(sub)
    build_summary_parser(sub)
    build_retention_parser(sub)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)
    args.func(args)


if __name__ == "__main__":
    main()
