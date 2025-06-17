from typing import Any
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str
    raw: Any | None
