"""CLI commands for managing ping-record retention."""

from __future__ import annotations

import argparse
import sys

from api_pulse.retention import prune_pings, prune_stats


def cmd_prune(args: argparse.Namespace) -> None:
    """Prune ping records older than N days."""
    try:
        deleted = prune_pings(days=args.days, url=args.url or None)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    scope = f" for {args.url}" if args.url else ""
    print(f"Pruned {deleted} ping record(s) older than {args.days} day(s){scope}.")


def cmd_retention_stats(args: argparse.Namespace) -> None:  # noqa: ARG001
    """Show remaining ping counts per endpoint."""
    stats = prune_stats()
    if not stats:
        print("No ping records found.")
        return
    print(f"{'Endpoint URL':<50} {'Pings':>6}")
    print("-" * 58)
    for url, count in sorted(stats.items()):
        print(f"{url:<50} {count:>6}")


def build_retention_parser(sub: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    # prune
    p_prune = sub.add_parser("prune", help="Remove old ping records")
    p_prune.add_argument(
        "--days",
        type=int,
        required=True,
        help="Delete records older than this many days",
    )
    p_prune.add_argument(
        "--url",
        default="",
        help="Limit pruning to a specific endpoint URL",
    )
    p_prune.set_defaults(func=cmd_prune)

    # stats
    p_stats = sub.add_parser("retention-stats", help="Show remaining ping counts")
    p_stats.set_defaults(func=cmd_retention_stats)
