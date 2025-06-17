import os
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


async def authorize(api_key: str = Depends(api_key_header)) -> None:
    expected_key = get_api_key()
    if api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key",
        )
