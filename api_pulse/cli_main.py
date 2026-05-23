"""Main CLI entry-point — registers all sub-command parsers."""

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
from api_pulse.cli_anomaly import build_anomaly_parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="api-pulse",
        description="Minimal REST-endpoint uptime monitor",
    )
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # Core commands
    add_p = sub.add_parser("add", help="Register a new endpoint")
    add_p.add_argument("url")
    add_p.add_argument("--name", default="")
    add_p.add_argument("--interval", type=int, default=60)
    add_p.set_defaults(func=cmd_add)

    list_p = sub.add_parser("list", help="List registered endpoints")
    list_p.set_defaults(func=cmd_list)

    report_p = sub.add_parser("report", help="Show latency report")
    report_p.add_argument("--limit", type=int, default=20)
    report_p.set_defaults(func=cmd_report)

    start_p = sub.add_parser("start", help="Start the polling scheduler")
    start_p.add_argument("--interval", type=int, default=None)
    start_p.set_defaults(func=cmd_start)

    # Feature sub-command groups
    build_export_parser(sub)
    build_alert_parser(sub)
    build_notify_parser(sub)
    build_history_parser(sub)
    build_summary_parser(sub)
    build_retention_parser(sub)
    build_anomaly_parser(sub)

    return parser


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":  # pragma: no cover
    main()
