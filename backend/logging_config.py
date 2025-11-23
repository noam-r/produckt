"""
Logging configuration for ProDuckt application.

Configures structured logging with timestamps, log levels, and proper formatting
for Docker container environments (stdout/stderr).
"""

import logging
import sys
from typing import Optional
from backend.config import settings


class ColoredFormatter(logging.Formatter):
    """
    Custom formatter that adds colors to log levels for better readability in development.
    Colors are disabled in production to avoid ANSI codes in log aggregation systems.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def __init__(self, *args, use_colors: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.use_colors = use_colors
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with optional colors."""
        if self.use_colors and record.levelname in self.COLORS:
            # Add color to level name
            record.levelname = f"{self.COLORS[record.levelname]}{record.levelname}{self.RESET}"
        
        return super().format(record)


def setup_logging(
    log_level: Optional[str] = None,
    use_colors: Optional[bool] = None
) -> None:
    """
    Configure application logging.
    
    Sets up structured logging with:
    - Timestamps in ISO format
    - Log levels
    - Module names
    - Colored output (development only)
    - Output to stdout/stderr for Docker compatibility
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
                   Defaults to settings.log_level.
        use_colors: Whether to use colored output. Defaults to True for development,
                    False for production.
    """
    # Determine log level
    if log_level is None:
        log_level = settings.log_level.upper()
    
    # Determine if colors should be used
    if use_colors is None:
        use_colors = settings.environment == "development"
    
    # Create formatter
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    formatter = ColoredFormatter(
        fmt=log_format,
        datefmt=date_format,
        use_colors=use_colors
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # Add stdout handler for INFO and below
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.setFormatter(formatter)
    
    # Filter to only show INFO and below on stdout
    class StdoutFilter(logging.Filter):
        def filter(self, record):
            return record.levelno < logging.WARNING
    
    stdout_handler.addFilter(StdoutFilter())
    root_logger.addHandler(stdout_handler)
    
    # Add stderr handler for WARNING and above
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)
    
    # Configure third-party loggers to reduce noise
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Disable default access logs
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.INFO)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured: level={log_level}, environment={settings.environment}, colors={use_colors}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__ of the module)
    
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
