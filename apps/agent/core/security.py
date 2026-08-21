"""
Security & Rate Limiting Module: SlowAPI rate limiting and API key authentication.
"""
import logging
from typing import Optional
from fastapi import Request, HTTPException, Security, Depends, status, WebSocket
from fastapi.security import APIKeyHeader, APIKeyQuery
from slowapi import Limiter
from slowapi.util import get_remote_address
from config import settings

logger = logging.getLogger("agent.security")

# Initialize SlowAPI Limiter
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
    headers_enabled=True
)

# API Key headers and query definitions
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
api_key_query = APIKeyQuery(name="api_key", auto_error=False)


async def verify_api_key(
    header_key: Optional[str] = Security(api_key_header),
    query_key: Optional[str] = Security(api_key_query),
) -> str:
    """
    HTTP Security dependency: Verifies X-API-Key header or query parameter if API_KEY_REQUIRED is enabled.
    """
    if not settings.API_KEY_REQUIRED:
        return "authenticated"

    token = header_key or query_key
    if not token or token != settings.AGENT_API_KEY:
        logger.warning(f"Unauthorized API access attempt with key: '{token}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key authorization token.",
            headers={"WWW-Authenticate": "ApiKey"}
        )

    return token


async def verify_websocket_api_key(websocket: WebSocket) -> bool:
    """
    WebSocket Security helper: Validates API token in query params or headers before connection acceptance.
    """
    if not settings.API_KEY_REQUIRED:
        return True

    api_key = websocket.query_params.get("api_key") or websocket.headers.get("x-api-key")
    if not api_key or api_key != settings.AGENT_API_KEY:
        logger.warning("Rejecting unauthorized WebSocket connection request.")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return False

    return True
