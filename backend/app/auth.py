from typing import Annotated

import httpx
from fastapi import Header, HTTPException, status

from .config import settings


async def require_user(
    authorization: Annotated[str | None, Header()] = None,
) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Authentication required",
        )

    token = authorization.split(" ", 1)[1].strip()

    if not token:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Authentication required",
        )

    supabase_url = settings.supabase_url.strip().rstrip("/")
    publishable_key = settings.supabase_publishable_key.strip()

    if not supabase_url or not publishable_key:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Authentication service is not configured",
        )

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                f"{supabase_url}/auth/v1/user",
                headers={
                    "Authorization": f"Bearer {token}",
                    "apikey": publishable_key,
                },
            )
    except httpx.HTTPError as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"Authentication service unavailable: {type(error).__name__}",
        ) from error

    if response.status_code != 200:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired session",
        )

    return response.json()