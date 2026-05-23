"""Thin integration shim: registers correlation commands into cli_main parser.

This module is imported by cli_main.build_parser so that 'api-pulse correlate'
works end-to-end without modifying the existing cli_main.py.
"""
from __future__ import annotations

from .cli_correlation import build_correlation_parser


def register(subparsers) -> None:
    """Register the 'correlate' sub-command onto *subparsers*."""
    build_correlation_parser(subparsers)
