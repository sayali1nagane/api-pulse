from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime


@dataclass
class Endpoint:
    url: str
    name: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row) -> "Endpoint":
        return cls(
            id=row["id"],
            name=row["name"],
            url=row["url"],
            created_at=row["created_at"],
        )


@dataclass
class PingResult:
    endpoint_id: int
    success: bool
    latency_ms: Optional[float] = None
    status_code: Optional[int] = None
    error: Optional[str] = None
    id: Optional[int] = None
    pinged_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row) -> "PingResult":
        return cls(
            id=row["id"],
            endpoint_id=row["endpoint_id"],
            status_code=row["status_code"],
            latency_ms=row["latency_ms"],
            success=bool(row["success"]),
            error=row["error"],
            pinged_at=row["pinged_at"],
        )

    def __str__(self) -> str:
        if self.success:
            return f"OK [{self.status_code}] {self.latency_ms:.1f}ms"
        return f"FAIL — {self.error or f'HTTP {self.status_code}'}"
