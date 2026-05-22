"""CLI integration for notification dispatch in api-pulse.

Adds the `notify` sub-command that runs alert checks and dispatches
results through configured channels.
"""

from __future__ import annotations

import argparse
import sys

from api_pulse.alerting import AlertRule, run_alerts
from api_pulse.db import db_session
from api_pulse.notifier import NotifierConfig, dispatch


def cmd_notify(args: argparse.Namespace) -> None:
    """Check alerts and dispatch notifications."""
    rule = AlertRule(
        min_pings=args.min_pings,
        failure_rate_threshold=args.threshold,
        window=args.window,
    )
    config = NotifierConfig(
        webhook_url=args.webhook or None,
        console=not args.quiet,
    )

    with db_session() as conn:
        alerts = run_alerts(conn, rule)

    if not alerts:
        if not args.quiet:
            print("No alerts triggered.", file=sys.stderr)
        return

    dispatch(alerts, config)
    if args.fail_on_alert:
        sys.exit(1)


def build_notify_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "notify",
        help="Run alert checks and dispatch notifications.",
    )
    p.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Failure-rate threshold (0-1) to trigger an alert (default: 0.5).",
    )
    p.add_argument(
        "--min-pings",
        type=int,
        default=5,
        dest="min_pings",
        help="Minimum number of pings required before alerting (default: 5).",
    )
    p.add_argument(
        "--window",
        type=int,
        default=20,
        help="Number of most-recent pings to evaluate (default: 20).",
    )
    p.add_argument(
        "--webhook",
        default="",
        help="Webhook URL to POST alert payloads to.",
    )
    p.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console output.",
    )
    p.add_argument(
        "--fail-on-alert",
        action="store_true",
        dest="fail_on_alert",
        help="Exit with code 1 if any alert is triggered.",
    )
    p.set_defaults(func=cmd_notify)
