"""CLI sub-commands for endpoint latency correlation analysis."""
from __future__ import annotations

import argparse
import sys

from .db import db_session
from .correlation import correlate_all, correlate_endpoints


def cmd_correlate(args: argparse.Namespace) -> None:
    with db_session() as conn:
        if args.url_a and args.url_b:
            result = correlate_endpoints(
                conn, args.url_a, args.url_b, limit=args.limit
            )
            print(result)
            if result.coefficient is None:
                sys.exit(2)
        else:
            results = correlate_all(conn, limit=args.limit)
            if not results:
                print("Not enough endpoints to correlate (need at least 2).")
                return
            for r in results:
                print(r)
            if args.fail_on_strong:
                strong = [
                    r
                    for r in results
                    if r.coefficient is not None and abs(r.coefficient) >= 0.8
                ]
                if strong:
                    print(
                        f"\n{len(strong)} strongly correlated pair(s) found.",
                        file=sys.stderr,
                    )
                    sys.exit(1)


def build_correlation_parser(subparsers) -> None:
    p = subparsers.add_parser(
        "correlate",
        help="Compute Pearson latency correlation between endpoint pairs.",
    )
    p.add_argument("--url-a", dest="url_a", default=None, help="First endpoint URL.")
    p.add_argument("--url-b", dest="url_b", default=None, help="Second endpoint URL.")
    p.add_argument(
        "--limit",
        type=int,
        default=60,
        help="Number of recent pings to consider (default: 60).",
    )
    p.add_argument(
        "--fail-on-strong",
        dest="fail_on_strong",
        action="store_true",
        default=False,
        help="Exit with code 1 if any strongly correlated pair (|r|>=0.8) is found.",
    )
    p.set_defaults(func=cmd_correlate)
