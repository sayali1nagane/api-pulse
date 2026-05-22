"""Command-line interface for api-pulse."""
import argparse
import signal
import sys
import logging

from api_pulse.db import init_db, db_session
from api_pulse.repository import add_endpoint, list_endpoints
from api_pulse.scheduler import PingScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def cmd_add(args: argparse.Namespace) -> None:
    init_db()
    with db_session() as conn:
        endpoint = add_endpoint(conn, url=args.url, name=args.name, interval_seconds=args.interval)
    print(f"Added endpoint: [{endpoint.id}] {endpoint.name} -> {endpoint.url}")


def cmd_list(args: argparse.Namespace) -> None:  # noqa: ARG001
    init_db()
    with db_session() as conn:
        endpoints = list_endpoints(conn)
    if not endpoints:
        print("No endpoints registered.")
        return
    print(f"{'ID':<5} {'Name':<20} {'URL':<40} {'Interval (s)':<14}")
    print("-" * 80)
    for ep in endpoints:
        print(f"{ep.id:<5} {ep.name:<20} {ep.url:<40} {ep.interval_seconds:<14}")


def cmd_start(args: argparse.Namespace) -> None:
    init_db()
    scheduler = PingScheduler(interval_seconds=args.interval)
    scheduler.start()
    logger.info("api-pulse running. Press Ctrl+C to stop.")

    def _shutdown(sig, frame):  # noqa: ARG001
        logger.info("Shutting down...")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)
    signal.pause()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="api-pulse",
        description="Minimal REST endpoint uptime monitor.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add_p = sub.add_parser("add", help="Register a new endpoint")
    add_p.add_argument("url", help="Endpoint URL to monitor")
    add_p.add_argument("--name", default="", help="Human-readable name")
    add_p.add_argument("--interval", type=int, default=60, help="Ping interval in seconds")
    add_p.set_defaults(func=cmd_add)

    list_p = sub.add_parser("list", help="List registered endpoints")
    list_p.set_defaults(func=cmd_list)

    start_p = sub.add_parser("start", help="Start the monitoring scheduler")
    start_p.add_argument("--interval", type=int, default=60, help="Global ping interval in seconds")
    start_p.set_defaults(func=cmd_start)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
