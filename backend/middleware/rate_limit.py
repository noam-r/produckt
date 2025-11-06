"""
Rate limiting middleware for API endpoints.

Simple in-memory rate limiter for POC. For production, use Redis-backed limiter
like slowapi or a proper API gateway.
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Dict, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import asyncio


class InMemoryRateLimiter:
    """
    Simple in-memory rate limiter using sliding window.

    WARNING: This is not suitable for production as:
    1. State is lost on server restart
    2. Does not scale across multiple server instances
    3. Memory usage grows with number of unique clients

    For production, use Redis with slowapi or similar.
    """

    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.window_size = timedelta(minutes=1)
        # Store: {client_id: [(timestamp1, timestamp2, ...)]}
        self._requests: Dict[str, list] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def is_allowed(self, client_id: str) -> Tuple[bool, int, int]:
        """
        Check if request is allowed for client.

        Args:
            client_id: Unique identifier for the client (e.g., user ID or IP)

        Returns:
            Tuple of (is_allowed, remaining_requests, retry_after_seconds)
        """
        async with self._lock:
            now = datetime.utcnow()
            window_start = now - self.window_size

            # Get requests for this client
            client_requests = self._requests[client_id]

            # Remove requests outside the current window
            client_requests[:] = [
                req_time for req_time in client_requests
                if req_time > window_start
            ]

            # Check if limit exceeded
            request_count = len(client_requests)

            if request_count >= self.requests_per_minute:
                # Calculate retry after (time until oldest request expires)
                if client_requests:
                    oldest_request = min(client_requests)
                    retry_after = int((oldest_request + self.window_size - now).total_seconds())
                    retry_after = max(1, retry_after)  # At least 1 second
                else:
                    retry_after = 60

                return False, 0, retry_after

            # Allow request and record it
            client_requests.append(now)
            remaining = self.requests_per_minute - request_count - 1

            return True, remaining, 0

    async def cleanup(self):
        """Remove expired entries to prevent memory growth."""
        async with self._lock:
            now = datetime.utcnow()
            window_start = now - self.window_size

            # Remove clients with no recent requests
            clients_to_remove = []
            for client_id, requests in self._requests.items():
                # Remove old requests
                requests[:] = [req for req in requests if req > window_start]

                # If no requests in window, mark for removal
                if not requests:
                    clients_to_remove.append(client_id)

            for client_id in clients_to_remove:
                del self._requests[client_id]


# Global rate limiter instance
rate_limiter = InMemoryRateLimiter(requests_per_minute=100)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits on API requests.

    Applies rate limiting based on:
    - Authenticated users: by user ID
    - Unauthenticated requests: by IP address

    Excludes:
    - Health check endpoints
    - Static files
    - Documentation
    """

    def __init__(self, app, limiter: InMemoryRateLimiter = None):
        super().__init__(app)
        self.limiter = limiter or rate_limiter

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""

        # Skip rate limiting for certain paths
        path = request.url.path
        if self._should_skip_rate_limit(path):
            return await call_next(request)

        # Determine client identifier
        client_id = await self._get_client_id(request)

        # Check rate limit
        is_allowed, remaining, retry_after = await self.limiter.is_allowed(client_id)

        if not is_allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
                headers={
                    "X-RateLimit-Limit": str(self.limiter.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(retry_after),
                    "Retry-After": str(retry_after)
                }
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response

    def _should_skip_rate_limit(self, path: str) -> bool:
        """Check if path should skip rate limiting."""
        skip_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/static",
        ]

        return any(path.startswith(skip_path) for skip_path in skip_paths)

    async def _get_client_id(self, request: Request) -> str:
        """
        Get unique client identifier for rate limiting.

        For authenticated requests, use user ID from session.
        For unauthenticated requests, use IP address.
        """
        # Check for session cookie
        session_id = request.cookies.get("session_id")

        if session_id:
            # Try to get user from session
            from backend.auth.session import session_manager

            session = session_manager.get_session(session_id)
            if session:
                return f"user:{session.user_id}"

        # Fall back to IP address for unauthenticated requests
        # Try to get real IP from reverse proxy headers
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # X-Forwarded-For can contain multiple IPs, take the first
            client_ip = forwarded.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        return f"ip:{client_ip}"


async def cleanup_rate_limiter():
    """Background task to cleanup expired rate limit entries."""
    while True:
        await asyncio.sleep(300)  # Run every 5 minutes
        await rate_limiter.cleanup()
