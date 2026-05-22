"""CLI entry point for api-pulse."""

import argparse
import signal
import sys

from api_pulse.db import db_session, init_db, get_connection
from api_pulse.repository import add_endpoint, list_endpoints
from api_pulse.scheduler import PingScheduler
from api_pulse.reporter import report_all, compute_stats


def cmd_add(args):
    with db_session() as conn:
        add_endpoint(conn, url=args.url, name=args.name)
    print(f"Added endpoint: {args.name} -> {args.url}")


def cmd_list(args):
    with db_session() as conn:
        endpoints = list_endpoints(conn)
    if not endpoints:
        print("No endpoints registered.")
        return
    for ep in endpoints:
        print(f"  [{ep.name}] {ep.url}  interval={ep.interval_seconds}s")


def cmd_report(args):
    with db_session() as conn:
        if args.url:
            endpoints = list_endpoints(conn)
            match = next((e for e in endpoints if e.url == args.url), None)
            if not match:
                print(f"Endpoint not found: {args.url}")
                sys.exit(1)
            stats = [compute_stats(conn, match.url, match.name, limit=args.limit)]
        else:
            stats = report_all(conn, limit=args.limit)

    if not stats:
        print("No endpoints to report on.")
        return

    for s in stats:
        print(str(s))
        print()


def cmd_start(args):
    conn = get_connection()
    init_db(conn)
    scheduler = PingScheduler(conn)

    def _shutdown(sig, frame):
        print("\nShutting down...")
        scheduler.stop()
        conn.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("Starting api-pulse scheduler. Press Ctrl+C to stop.")
    scheduler.start()
    signal.pause()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="api-pulse",
        description="Minimal REST endpoint uptime monitor",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="Register a new endpoint")
    p_add.add_argument("url", help="Endpoint URL")
    p_add.add_argument("--name", default="", help="Human-readable name")
    p_add.set_defaults(func=cmd_add)

    p_list = sub.add_parser("list", help="List registered endpoints")
    p_list.set_defaults(func=cmd_list)

    p_report = sub.add_parser("report", help="Show latency and uptime stats")
    p_report.add_argument("--url", default=None, help="Filter to a specific endpoint URL")
    p_report.add_argument("--limit", type=int, default=50, help="Number of recent pings to analyse")
    p_report.set_defaults(func=cmd_report)

    p_start = sub.add_parser("start", help="Start the monitoring scheduler")
    p_start.set_defaults(func=cmd_start)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
