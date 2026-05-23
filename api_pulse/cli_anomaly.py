"""CLI sub-commands for anomaly detection."""

from __future__ import annotations

import argparse
import sys

from api_pulse.anomaly import scan_anomalies, DEFAULT_SIGMA_THRESHOLD
from api_pulse.db import db_session


def cmd_scan_anomalies(args: argparse.Namespace) -> None:
    """Scan all endpoints for latency anomalies and print results."""
    with db_session() as conn:
        anomalies = scan_anomalies(
            conn,
            sigma_threshold=args.sigma,
            lookback=args.lookback,
        )

    if not anomalies:
        print("No anomalies detected.")
        return

    print(f"Detected {len(anomalies)} anomaly(ies):")
    for a in anomalies:
        print(f"  {a}")

    if args.fail_on_anomaly:
        sys.exit(1)


def build_anomaly_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "scan-anomalies",
        help="Detect endpoints whose latest latency is an outlier vs baseline",
    )
    p.add_argument(
        "--sigma",
        type=float,
        default=DEFAULT_SIGMA_THRESHOLD,
        metavar="N",
        help=f"Standard-deviation threshold (default: {DEFAULT_SIGMA_THRESHOLD})",
    )
    p.add_argument(
        "--lookback",
        type=int,
        default=60,
        metavar="N",
        help="Number of recent pings used to compute std-dev (default: 60)",
    )
    p.add_argument(
        "--fail-on-anomaly",
        action="store_true",
        default=False,
        help="Exit with status 1 if any anomaly is found",
    )
    p.set_defaults(func=cmd_scan_anomalies)
