"""Simple alerting module: detects endpoints whose recent failure rate
exceeds a configurable threshold and emits console warnings."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from api_pulse.repository import list_endpoints, get_recent_pings


@dataclass
class AlertRule:
    """Configuration for a single alert rule."""
    failure_rate_threshold: float = 0.5   # 0.0 – 1.0
    min_pings: int = 3                    # ignore endpoints with fewer pings
    window: int = 10                      # how many recent pings to inspect


@dataclass
class Alert:
    """Represents a triggered alert for one endpoint."""
    url: str
    failure_rate: float
    total_checked: int

    def __str__(self) -> str:  # pragma: no cover
        pct = self.failure_rate * 100
        return (
            f"[ALERT] {self.url} — {pct:.1f}% failures "
            f"in last {self.total_checked} pings"
        )


def check_endpoint(
    url: str,
    conn,
    rule: AlertRule,
) -> Optional[Alert]:
    """Return an Alert if the endpoint breaches the rule, else None."""
    pings = get_recent_pings(conn, url, limit=rule.window)
    if len(pings) < rule.min_pings:
        return None
    failures = sum(1 for p in pings if not p.success)
    rate = failures / len(pings)
    if rate >= rule.failure_rate_threshold:
        return Alert(url=url, failure_rate=rate, total_checked=len(pings))
    return None


def run_alerts(
    conn,
    rule: Optional[AlertRule] = None,
) -> List[Alert]:
    """Check all endpoints and return a list of triggered alerts."""
    if rule is None:
        rule = AlertRule()
    endpoints = list_endpoints(conn)
    alerts: List[Alert] = []
    for ep in endpoints:
        alert = check_endpoint(ep.url, conn, rule)
        if alert:
            alerts.append(alert)
    return alerts
