"""Correlation analysis: compare latency trends across multiple endpoints."""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from .db import db_session
from .repository import list_endpoints, get_recent_pings


@dataclass
class CorrelationResult:
    url_a: str
    url_b: str
    coefficient: Optional[float]  # Pearson r, None if not enough data
    sample_size: int

    def __str__(self) -> str:
        if self.coefficient is None:
            return f"{self.url_a} <-> {self.url_b}: insufficient data (n={self.sample_size})"
        strength = _describe(self.coefficient)
        return (
            f"{self.url_a} <-> {self.url_b}: "
            f"r={self.coefficient:+.3f} ({strength}, n={self.sample_size})"
        )


def _describe(r: float) -> str:
    abs_r = abs(r)
    if abs_r >= 0.8:
        return "strong"
    if abs_r >= 0.5:
        return "moderate"
    if abs_r >= 0.2:
        return "weak"
    return "negligible"


def _pearson(xs: List[float], ys: List[float]) -> Optional[float]:
    n = len(xs)
    if n < 3:
        return None
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    den_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if den_x == 0 or den_y == 0:
        return None
    return num / (den_x * den_y)


def correlate_endpoints(
    conn, url_a: str, url_b: str, limit: int = 60
) -> CorrelationResult:
    """Return Pearson correlation of latencies between two endpoints."""
    pings_a = [
        p.latency_ms for p in get_recent_pings(conn, url_a, limit) if p.latency_ms is not None
    ]
    pings_b = [
        p.latency_ms for p in get_recent_pings(conn, url_b, limit) if p.latency_ms is not None
    ]
    # Align to shortest series
    n = min(len(pings_a), len(pings_b))
    xs, ys = pings_a[:n], pings_b[:n]
    coeff = _pearson(xs, ys)
    return CorrelationResult(url_a=url_a, url_b=url_b, coefficient=coeff, sample_size=n)


def correlate_all(conn, limit: int = 60) -> List[CorrelationResult]:
    """Compute pairwise correlations for all monitored endpoints."""
    endpoints = list_endpoints(conn)
    results: List[CorrelationResult] = []
    for i, ep_a in enumerate(endpoints):
        for ep_b in endpoints[i + 1 :]:
            results.append(correlate_endpoints(conn, ep_a.url, ep_b.url, limit=limit))
    return results
