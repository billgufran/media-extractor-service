from pydantic import BaseModel
from typing import Any, Optional


class ErrorResponse(BaseModel):
    """Standard error response model."""

    error: str
    raw: Optional[Any]
