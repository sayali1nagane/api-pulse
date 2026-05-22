import time
import logging
from threading import Thread, Event
from typing import Optional

from api_pulse.db import db_session
from api_pulse.pinger import ping_all
from api_pulse.repository import list_endpoints

logger = logging.getLogger(__name__)


class PingScheduler:
    """Periodically pings all registered endpoints at a given interval."""

    def __init__(self, interval_seconds: int = 60):
        self.interval = interval_seconds
        self._stop_event = Event()
        self._thread: Optional[Thread] = None

    def _run(self) -> None:
        logger.info("Scheduler started (interval=%ds)", self.interval)
        while not self._stop_event.is_set():
            try:
                with db_session() as conn:
                    endpoints = list_endpoints(conn)
                if endpoints:
                    ping_all(endpoints)
                else:
                    logger.debug("No endpoints registered, skipping cycle.")
            except Exception as exc:  # pylint: disable=broad-except
                logger.error("Error during ping cycle: %s", exc)
            self._stop_event.wait(timeout=self.interval)
        logger.info("Scheduler stopped.")

    def start(self) -> None:
        """Start the background scheduling thread."""
        if self._thread and self._thread.is_alive():
            logger.warning("Scheduler is already running.")
            return
        self._stop_event.clear()
        self._thread = Thread(target=self._run, daemon=True, name="ping-scheduler")
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the scheduler to stop and wait for the thread to finish."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
            self._thread = None

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()
