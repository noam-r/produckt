"""
Request logging middleware for tracking HTTP requests.

Logs all incoming HTTP requests with method, path, status code, response time,
and client information for debugging and monitoring purposes.
"""

import time
import logging
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log HTTP requests and responses.
    
    Logs:
    - Request method and path
    - Query parameters
    - Client IP address
    - Response status code
    - Response time in milliseconds
    - User information (if authenticated)
    
    Excludes health check endpoints to reduce log noise.
    """
    
    def __init__(
        self,
        app: ASGIApp,
        skip_paths: list[str] | None = None
    ):
        """
        Initialize request logging middleware.
        
        Args:
            app: ASGI application
            skip_paths: List of path prefixes to skip logging (e.g., ["/health", "/metrics"])
        """
        super().__init__(app)
        self.skip_paths = skip_paths or ["/health"]
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and log details.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware or route handler
        
        Returns:
            HTTP response
        """
        # Check if we should skip logging for this path
        if self._should_skip_logging(request.url.path):
            return await call_next(request)
        
        # Record start time
        start_time = time.time()
        
        # Extract request information
        method = request.method
        path = request.url.path
        query_params = str(request.query_params) if request.query_params else ""
        client_ip = self._get_client_ip(request)
        
        # Get user information if available
        user_info = await self._get_user_info(request)
        
        # Log request
        logger.info(
            f"Request started: {method} {path}",
            extra={
                "method": method,
                "path": path,
                "query_params": query_params,
                "client_ip": client_ip,
                "user_id": user_info.get("user_id"),
                "user_email": user_info.get("user_email"),
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate response time
            duration_ms = (time.time() - start_time) * 1000
            
            # Log response
            log_level = self._get_log_level_for_status(response.status_code)
            logger.log(
                log_level,
                f"Request completed: {method} {path} - {response.status_code} - {duration_ms:.2f}ms",
                extra={
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                    "user_id": user_info.get("user_id"),
                }
            )
            
            return response
            
        except Exception as e:
            # Calculate response time even for errors
            duration_ms = (time.time() - start_time) * 1000
            
            # Log error
            logger.error(
                f"Request failed: {method} {path} - {type(e).__name__}: {str(e)} - {duration_ms:.2f}ms",
                extra={
                    "method": method,
                    "path": path,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": duration_ms,
                    "client_ip": client_ip,
                    "user_id": user_info.get("user_id"),
                },
                exc_info=True
            )
            
            # Re-raise the exception to be handled by FastAPI
            raise
    
    def _should_skip_logging(self, path: str) -> bool:
        """
        Check if path should skip request logging.
        
        Args:
            path: Request path
        
        Returns:
            True if logging should be skipped
        """
        return any(path.startswith(skip_path) for skip_path in self.skip_paths)
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP address from request.
        
        Checks X-Forwarded-For header first (for reverse proxy setups),
        then falls back to direct client IP.
        
        Args:
            request: HTTP request
        
        Returns:
            Client IP address
        """
        # Check for X-Forwarded-For header (reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # X-Forwarded-For can contain multiple IPs, take the first (original client)
            return forwarded.split(",")[0].strip()
        
        # Check for X-Real-IP header (alternative reverse proxy header)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fall back to direct client IP
        return request.client.host if request.client else "unknown"
    
    async def _get_user_info(self, request: Request) -> dict:
        """
        Extract user information from request session.
        
        Args:
            request: HTTP request
        
        Returns:
            Dictionary with user_id and user_email if authenticated, empty dict otherwise
        """
        try:
            # Check for session cookie
            session_id = request.cookies.get("session_id")
            if not session_id:
                return {}
            
            # Get session
            from backend.auth.session import session_manager
            session = session_manager.get_session(session_id)
            if not session:
                return {}
            
            # Return user info
            return {
                "user_id": session.user_id,
                "user_email": session.user_email,
            }
        except Exception:
            # If anything fails, just return empty dict
            # We don't want logging to break the request
            return {}
    
    def _get_log_level_for_status(self, status_code: int) -> int:
        """
        Determine appropriate log level based on HTTP status code.
        
        Args:
            status_code: HTTP status code
        
        Returns:
            Logging level (INFO, WARNING, or ERROR)
        """
        if status_code < 400:
            return logging.INFO
        elif status_code < 500:
            return logging.WARNING
        else:
            return logging.ERROR
