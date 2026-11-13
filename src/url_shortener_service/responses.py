from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, Field


class SuccessResponse(BaseModel):
    status_code: int
    status: str = "success"
    message: str
    data: dict[str, Any] | list[Any] | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
