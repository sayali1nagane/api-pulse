"""Notification dispatch for api-pulse alerts.

Currently supports console (stderr) and webhook (HTTP POST) channels.
"""

from __future__ import annotations

import json
import sys
import urllib.request
import urllib.error
from dataclasses import dataclass, field
from typing import List, Optional

from api_pulse.alerting import Alert


@dataclass
class NotifierConfig:
    """Configuration for one or more notification channels."""
    webhook_url: Optional[str] = None
    webhook_timeout: int = 5
    console: bool = True
    extra_headers: dict = field(default_factory=dict)


def notify_console(alert: Alert) -> None:
    """Write alert to stderr."""
    print(f"[ALERT] {alert}", file=sys.stderr)


def notify_webhook(alert: Alert, config: NotifierConfig) -> bool:
    """POST alert as JSON to a webhook URL.

    Returns True on success, False on failure.
    """
    if not config.webhook_url:
        return False

    payload = json.dumps({
        "url": alert.url,
        "failure_rate": round(alert.failure_rate, 4),
        "threshold": alert.threshold,
        "message": str(alert),
    }).encode()

    headers = {"Content-Type": "application/json", **config.extra_headers}
    req = urllib.request.Request(
        config.webhook_url, data=payload, headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=config.webhook_timeout):
            return True
    except (urllib.error.URLError, OSError):
        return False


def dispatch(alerts: List[Alert], config: NotifierConfig) -> None:
    """Dispatch a list of alerts through all configured channels."""
    for alert in alerts:
        if config.console:
            notify_console(alert)
        if config.webhook_url:
            notify_webhook(alert, config)
