# ProDuckt Logging Guide

This document describes the logging system implemented in ProDuckt for debugging and monitoring.

## Overview

ProDuckt uses Python's built-in `logging` module with structured logging that outputs to stdout/stderr for Docker compatibility. The logging system provides:

- **Structured logs** with timestamps, log levels, and module names
- **Colored output** in development for better readability
- **Request logging** for all HTTP requests with timing information
- **Separate streams** (stdout for INFO/DEBUG, stderr for WARNING/ERROR)
- **Docker-friendly** output that integrates with `docker-compose logs`

## Log Levels

The application supports standard Python log levels:

- **DEBUG**: Detailed information for diagnosing problems (development only)
- **INFO**: General informational messages about application flow
- **WARNING**: Warning messages for potentially problematic situations
- **ERROR**: Error messages for serious problems
- **CRITICAL**: Critical messages for very serious errors

Configure the log level via the `LOG_LEVEL` environment variable in `.env`:

```bash
LOG_LEVEL=DEBUG  # For development
LOG_LEVEL=INFO   # For production
```

## Configuration

### Environment Variables

```bash
# Set log level
LOG_LEVEL=INFO

# Set environment (affects color output)
ENVIRONMENT=development  # Colored output enabled
ENVIRONMENT=production   # Colored output disabled
```

### Programmatic Configuration

The logging system is automatically configured when the application starts via `backend/main.py`:

```python
from backend.logging_config import setup_logging

# Configure logging at application startup
setup_logging()
```

You can also configure it manually:

```python
from backend.logging_config import setup_logging

# Custom configuration
setup_logging(
    log_level="DEBUG",
    use_colors=True
)
```

## Using Logging in Code

### Basic Usage

```python
import logging

# Get a logger for your module
logger = logging.getLogger(__name__)

# Log messages at different levels
logger.debug("Detailed debug information")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical error")
```

### Logging with Context

```python
# Log with extra context
logger.info(
    "User logged in",
    extra={
        "user_id": user.id,
        "email": user.email,
        "ip_address": request.client.host
    }
)
```

### Logging Exceptions

```python
try:
    # Some operation
    result = risky_operation()
except Exception as e:
    # Log with full traceback
    logger.error(
        f"Operation failed: {str(e)}",
        exc_info=True  # Include full traceback
    )
    raise
```

## Request Logging

All HTTP requests are automatically logged by the `RequestLoggingMiddleware`. Each request logs:

- Request method and path
- Query parameters
- Client IP address
- User information (if authenticated)
- Response status code
- Response time in milliseconds

### Example Request Logs

```
2024-11-20 10:30:15 - backend.middleware.request_logging - INFO - Request started: GET /api/initiatives
2024-11-20 10:30:15 - backend.middleware.request_logging - INFO - Request completed: GET /api/initiatives - 200 - 45.23ms
```

### Skipping Request Logging

By default, health check endpoints are not logged to reduce noise. To skip logging for additional paths:

```python
from backend.middleware.request_logging import RequestLoggingMiddleware

app.add_middleware(
    RequestLoggingMiddleware,
    skip_paths=["/health", "/metrics", "/static"]
)
```

## Viewing Logs

### Docker Compose

View logs from all services:
```bash
docker-compose logs
```

View logs from a specific service:
```bash
docker-compose logs backend
docker-compose logs frontend
```

Follow logs in real-time:
```bash
docker-compose logs -f backend
```

View last N lines:
```bash
docker-compose logs --tail=100 backend
```

Filter by log level (requires grep):
```bash
docker-compose logs backend | grep ERROR
docker-compose logs backend | grep WARNING
```

### Docker Container

View logs from a running container:
```bash
docker logs <container-id>
docker logs produck-backend-1
```

Follow logs:
```bash
docker logs -f produck-backend-1
```

### Local Development (Non-Docker)

When running locally, logs appear directly in your terminal:
```bash
uvicorn backend.main:app --reload
```

## Log Format

### Development Format (Colored)

```
2024-11-20 10:30:15 - backend.main - INFO - Starting ProDuckt API - Environment: development
2024-11-20 10:30:15 - backend.database - INFO - Configuring SQLite database: sqlite:////app/data/produck.db
2024-11-20 10:30:16 - backend.main - INFO - ProDuckt API startup complete
```

### Production Format (No Colors)

```
2024-11-20 10:30:15 - backend.main - INFO - Starting ProDuckt API - Environment: production
2024-11-20 10:30:15 - backend.database - INFO - Configuring PostgreSQL database with connection pooling
2024-11-20 10:30:16 - backend.main - INFO - ProDuckt API startup complete
```

## Log Output Streams

The logging system uses two output streams:

- **stdout**: INFO and DEBUG messages
- **stderr**: WARNING, ERROR, and CRITICAL messages

This separation allows for:
- Easy filtering in log aggregation systems
- Separate handling of errors vs. informational logs
- Better integration with Docker and Kubernetes

## Third-Party Library Logging

The logging configuration automatically adjusts log levels for third-party libraries to reduce noise:

- **uvicorn**: INFO level (access logs disabled)
- **fastapi**: INFO level
- **sqlalchemy**: WARNING level (query logs in development only)
- **anthropic**: INFO level

## Best Practices

### 1. Use Appropriate Log Levels

```python
# DEBUG: Detailed diagnostic information
logger.debug(f"Processing item {item_id} with config {config}")

# INFO: General flow of the application
logger.info(f"User {user_id} created initiative {initiative_id}")

# WARNING: Potentially problematic situations
logger.warning(f"Rate limit approaching for user {user_id}")

# ERROR: Errors that need attention
logger.error(f"Failed to generate MRD: {str(e)}", exc_info=True)

# CRITICAL: Very serious errors
logger.critical(f"Database connection lost")
```

### 2. Include Context

```python
# Good: Includes relevant context
logger.info(
    f"MRD generated successfully",
    extra={
        "initiative_id": initiative.id,
        "user_id": user.id,
        "generation_time_ms": duration_ms
    }
)

# Bad: Lacks context
logger.info("MRD generated")
```

### 3. Log Exceptions Properly

```python
# Good: Includes exception details and traceback
try:
    result = operation()
except Exception as e:
    logger.error(
        f"Operation failed: {str(e)}",
        exc_info=True  # Include full traceback
    )
    raise

# Bad: Loses exception information
except Exception as e:
    logger.error("Operation failed")
```

### 4. Avoid Logging Sensitive Data

```python
# Good: Masks sensitive data
logger.info(f"API key configured: {api_key[:8]}...")

# Bad: Logs full API key
logger.info(f"API key: {api_key}")
```

### 5. Use Structured Logging

```python
# Good: Structured data in extra
logger.info(
    "Payment processed",
    extra={
        "amount": 100.00,
        "currency": "USD",
        "user_id": user.id
    }
)

# Acceptable: Formatted string
logger.info(f"Payment processed: ${100.00} USD for user {user.id}")
```

## Troubleshooting

### Logs Not Appearing

1. Check log level configuration:
   ```bash
   echo $LOG_LEVEL
   ```

2. Verify logging is configured:
   ```python
   import logging
   logger = logging.getLogger(__name__)
   logger.info("Test message")
   ```

3. Check if logs are going to stderr:
   ```bash
   docker-compose logs backend 2>&1 | grep "Test message"
   ```

### Too Much Log Output

1. Increase log level to reduce verbosity:
   ```bash
   LOG_LEVEL=WARNING  # Only warnings and errors
   ```

2. Filter logs by service:
   ```bash
   docker-compose logs backend | grep ERROR
   ```

3. Disable third-party library logs:
   ```python
   logging.getLogger("uvicorn").setLevel(logging.WARNING)
   logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
   ```

### Colors Not Working

Colors are automatically disabled in production. To force enable/disable:

```python
from backend.logging_config import setup_logging

# Force enable colors
setup_logging(use_colors=True)

# Force disable colors
setup_logging(use_colors=False)
```

## Integration with Monitoring Tools

### Log Aggregation

The structured logging format works well with log aggregation tools:

- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Splunk**
- **Datadog**
- **CloudWatch Logs**
- **Grafana Loki**

### Example: Shipping Logs to CloudWatch

```yaml
# docker-compose.yml
services:
  backend:
    logging:
      driver: awslogs
      options:
        awslogs-region: us-east-1
        awslogs-group: produck-backend
        awslogs-stream: backend
```

### Example: JSON Logging for Structured Parsing

For production environments with log aggregation, you may want JSON-formatted logs:

```python
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        return json.dumps(log_data)
```

## Performance Considerations

### Log Level in Production

Use `INFO` or `WARNING` in production to avoid performance overhead:

```bash
# Production
LOG_LEVEL=INFO

# Development
LOG_LEVEL=DEBUG
```

### Conditional Debug Logging

For expensive debug operations:

```python
if logger.isEnabledFor(logging.DEBUG):
    # Only compute this if DEBUG is enabled
    debug_info = expensive_debug_operation()
    logger.debug(f"Debug info: {debug_info}")
```

### Avoid String Formatting in Hot Paths

```python
# Good: Lazy evaluation
logger.debug("Processing %s items", len(items))

# Bad: Always evaluates even if DEBUG is disabled
logger.debug(f"Processing {len(items)} items")
```

## Summary

The ProDuckt logging system provides comprehensive logging capabilities for debugging and monitoring:

- ✅ Structured logs with timestamps and levels
- ✅ Colored output in development
- ✅ Automatic request logging with timing
- ✅ Docker-friendly stdout/stderr output
- ✅ Configurable via environment variables
- ✅ Integration with log aggregation tools

For questions or issues, refer to the main documentation or open an issue on GitHub.
