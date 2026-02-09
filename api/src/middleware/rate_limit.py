"""
Rate limiting middleware using SlowAPI.
"""

import os

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware


def get_client_ip(request: Request) -> str:
    """
    Get the client IP address, handling proxies.

    Checks X-Forwarded-For header for reverse proxy setups
    (e.g., Fly.io, Cloud Run, nginx).

    Args:
        request: FastAPI request object

    Returns:
        Client IP address string
    """
    # Check for forwarded header (set by reverse proxies)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For can contain multiple IPs; first is the client
        return forwarded.split(",")[0].strip()

    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    # Fall back to direct client
    if request.client:
        return request.client.host

    return "unknown"


# Read rate limit from env (set in fly.toml or .env)
_rate_limit = os.getenv("RATE_LIMIT", "5/minute")

# Create the limiter instance with custom key function
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=[_rate_limit],
    storage_uri="memory://",  # In-memory storage (use redis:// for distributed)
)


def setup_rate_limiting(app: FastAPI) -> None:
    """
    Configure rate limiting for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
