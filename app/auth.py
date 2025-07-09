import os
import time
from collections import deque
from fastapi import Depends, HTTPException, status
from fastapi.security.api_key import APIKeyHeader


def get_api_key() -> str:
    api_key = os.getenv("MEDIA_EXTRACTOR_API_KEY")
    if not api_key:
        raise RuntimeError(
            "MEDIA_EXTRACTOR_API_KEY is not set in environment variables."
        )
    return api_key


api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

PUBLIC_API_KEY = os.getenv("MEDIA_EXTRACTOR_PUBLIC_API_KEY")
_public_key_requests: deque[float] = deque()
RATE_LIMIT_REQUESTS = 2
RATE_LIMIT_WINDOW = 15 * 60  # 15 minutes in seconds


def _is_public_key_limited() -> bool:
    """Return True if the public key has exceeded the rate limit."""
    now = time.monotonic()
    while _public_key_requests and now - _public_key_requests[0] > RATE_LIMIT_WINDOW:
        _public_key_requests.popleft()
    if len(_public_key_requests) >= RATE_LIMIT_REQUESTS:
        return True
    _public_key_requests.append(now)
    return False


async def authorize(api_key: str = Depends(api_key_header)) -> None:
    expected_key = get_api_key()

    if PUBLIC_API_KEY and api_key == PUBLIC_API_KEY:
        if _is_public_key_limited():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded: 2 requests per 15 minutes.",
            )
        return

    if api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
