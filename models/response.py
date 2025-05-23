from pydantic import BaseModel
from typing import  Any, Optional

class ErrorResponse(BaseModel):
    error: str
    raw: Optional[Any]