"""CLI sub-commands for the alerting feature."""

from __future__ import annotations

import argparse
import sys

from api_pulse.db import db_session
from api_pulse.alerting import AlertRule, run_alerts


def cmd_check_alerts(args: argparse.Namespace) -> None:
    """Check all endpoints for alert conditions and print results."""
    rule = AlertRule(
        failure_rate_threshold=args.threshold,
        min_pings=args.min_pings,
        window=args.window,
    )

    with db_session() as conn:
        alerts = run_alerts(conn, rule)

    if not alerts:
        print("All endpoints within acceptable failure rates.")
        return

    print(f"{len(alerts)} alert(s) triggered:\n")
    for alert in alerts:
        print(f"  {alert}")

    sys.exit(1)  # non-zero exit so CI / scripts can detect alert state


def build_alert_parser(subparsers) -> None:  # type: ignore[type-arg]
    """Register the 'alerts' sub-command onto an existing subparsers object."""
    p: argparse.ArgumentParser = subparsers.add_parser(
        "alerts",
        help="Check endpoints for high failure rates and print alerts.",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        metavar="RATE",
        help="Failure-rate threshold (0.0–1.0) that triggers an alert (default: 0.5).",
    )
    p.add_argument(
        "--min-pings",
        dest="min_pings",
        type=int,
        default=3,
        metavar="N",
        help="Minimum number of recent pings required to evaluate an alert (default: 3).",
    )
    p.add_argument(
        "--window",
        type=int,
        default=10,
        metavar="N",
        help="Number of most-recent pings to inspect per endpoint (default: 10).",
    )
    p.set_defaults(func=cmd_check_alerts)


if __name__ == "__main__":  # pragma: no cover
    parser = argparse.ArgumentParser(prog="api-pulse-alerts")
    subs = parser.add_subparsers(dest="command")
    build_alert_parser(subs)
    parsed = parser.parse_args()
    if hasattr(parsed, "func"):
        parsed.func(parsed)
    else:
        parser.print_help()
