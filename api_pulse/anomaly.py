"""Anomaly detection: flag pings whose latency deviates significantly from baseline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from api_pulse.baseline import get_baseline
from api_pulse.repository import get_recent_pings


DEFAULT_SIGMA_THRESHOLD = 2.0  # flag if latency > baseline_avg + threshold * baseline_std
DEFAULT_MIN_PINGS = 5          # minimum historical pings needed to compute a baseline


@dataclass
class Anomaly:
    url: str
    latency_ms: float
    baseline_avg_ms: float
    baseline_std_ms: float
    sigma: float

    def __str__(self) -> str:
        return (
            f"[ANOMALY] {self.url} — latency {self.latency_ms:.1f} ms "
            f"({self.sigma:.2f}σ above baseline avg {self.baseline_avg_ms:.1f} ms)"
        )


def _std(values: List[float]) -> float:
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return variance ** 0.5


def detect_anomaly(
    conn,
    url: str,
    latency_ms: float,
    sigma_threshold: float = DEFAULT_SIGMA_THRESHOLD,
    lookback: int = 60,
) -> Optional[Anomaly]:
    """Return an Anomaly if *latency_ms* is an outlier relative to recent history."""
    baseline = get_baseline(conn, url)
    if baseline is None:
        return None

    recent = get_recent_pings(conn, url, limit=lookback)
    successful = [p.latency_ms for p in recent if p.success and p.latency_ms is not None]
    if len(successful) < DEFAULT_MIN_PINGS:
        return None

    std = _std(successful)
    if std == 0.0:
        return None

    sigma = (latency_ms - baseline.avg_ms) / std
    if sigma >= sigma_threshold:
        return Anomaly(
            url=url,
            latency_ms=latency_ms,
            baseline_avg_ms=baseline.avg_ms,
            baseline_std_ms=std,
            sigma=sigma,
        )
    return None


def scan_anomalies(
    conn,
    sigma_threshold: float = DEFAULT_SIGMA_THRESHOLD,
    lookback: int = 60,
) -> List[Anomaly]:
    """Scan the most-recent successful ping for every tracked endpoint."""
    from api_pulse.repository import list_endpoints

    anomalies: List[Anomaly] = []
    for endpoint in list_endpoints(conn):
        pings = get_recent_pings(conn, endpoint.url, limit=1)
        if not pings or not pings[0].success or pings[0].latency_ms is None:
            continue
        result = detect_anomaly(conn, endpoint.url, pings[0].latency_ms, sigma_threshold, lookback)
        if result:
            anomalies.append(result)
    return anomalies
