import time
import requests
from datetime import datetime, timezone
from typing import Optional

from api_pulse.models import Endpoint, PingResult


DEFAULT_TIMEOUT = 10  # seconds


def ping_endpoint(endpoint: Endpoint, timeout: int = DEFAULT_TIMEOUT) -> PingResult:
    """Ping a single endpoint and return a PingResult with latency and status."""
    start = time.monotonic()
    status_code: Optional[int] = None
    error: Optional[str] = None
    success = False

    try:
        response = requests.get(endpoint.url, timeout=timeout)
        status_code = response.status_code
        success = response.ok
    except requests.exceptions.Timeout:
        error = "Request timed out"
    except requests.exceptions.ConnectionError as exc:
        error = f"Connection error: {exc}"
    except requests.exceptions.RequestException as exc:
        error = f"Request failed: {exc}"
    finally:
        elapsed_ms = round((time.monotonic() - start) * 1000, 2)

    return PingResult(
        id=None,
        endpoint_id=endpoint.id,
        timestamp=datetime.now(timezone.utc).isoformat(),
        latency_ms=elapsed_ms,
        status_code=status_code,
        success=success,
        error=error,
    )


def ping_all(endpoints: list[Endpoint], timeout: int = DEFAULT_TIMEOUT) -> list[PingResult]:
    """Ping all provided endpoints and return a list of PingResults."""
    results = []
    for endpoint in endpoints:
        result = ping_endpoint(endpoint, timeout=timeout)
        results.append(result)
    return results
