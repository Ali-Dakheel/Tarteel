from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader

from app.config import settings

_header = APIKeyHeader(name="X-Internal-Key", auto_error=False)


async def verify_internal_key(
    api_key: Annotated[str | None, Depends(_header)] = None,
) -> None:
    if api_key != settings.INTERNAL_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden",
        )
