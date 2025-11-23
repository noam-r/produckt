#!/bin/bash
# ============================================================================
# ProDuckt Backend Docker Entrypoint Script
# ============================================================================
# This script runs before the main application starts
# It handles database migrations and initialization
# ============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         ProDuckt Backend Container Starting              ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# Environment Validation
# ============================================================================

echo -e "${BLUE}[INFO]${NC} Validating environment configuration..."

VALIDATION_FAILED=false

# Check SECRET_KEY
if [ -z "$SECRET_KEY" ]; then
    echo -e "${RED}[ERROR]${NC} SECRET_KEY environment variable is not set"
    echo -e "${YELLOW}[HINT]${NC} Add SECRET_KEY to your .env file"
    echo -e "${YELLOW}[HINT]${NC} Generate a secure key with: openssl rand -hex 32"
    VALIDATION_FAILED=true
elif [ "$SECRET_KEY" = "change-me-to-a-secure-32-char-minimum-key" ]; then
    echo -e "${RED}[ERROR]${NC} SECRET_KEY is still using the default value"
    echo -e "${YELLOW}[HINT]${NC} Update SECRET_KEY in your .env file to a secure random string"
    echo -e "${YELLOW}[HINT]${NC} Generate one with: openssl rand -hex 32"
    VALIDATION_FAILED=true
elif [ ${#SECRET_KEY} -lt 32 ]; then
    echo -e "${YELLOW}[WARN]${NC} SECRET_KEY is shorter than 32 characters (current: ${#SECRET_KEY})"
    echo -e "${YELLOW}[HINT]${NC} For better security, use at least 32 characters"
    echo -e "${YELLOW}[HINT]${NC} Generate one with: openssl rand -hex 32"
fi

# Check ANTHROPIC_API_KEY
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}[ERROR]${NC} ANTHROPIC_API_KEY environment variable is not set"
    echo -e "${YELLOW}[HINT]${NC} Add ANTHROPIC_API_KEY to your .env file"
    echo -e "${YELLOW}[HINT]${NC} Get your API key from: https://console.anthropic.com/"
    VALIDATION_FAILED=true
elif [ "$ANTHROPIC_API_KEY" = "sk-ant-your-key-here" ]; then
    echo -e "${RED}[ERROR]${NC} ANTHROPIC_API_KEY is still using the placeholder value"
    echo -e "${YELLOW}[HINT]${NC} Update ANTHROPIC_API_KEY in your .env file with your actual API key"
    echo -e "${YELLOW}[HINT]${NC} Get your API key from: https://console.anthropic.com/"
    VALIDATION_FAILED=true
fi

# Check DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo -e "${YELLOW}[WARN]${NC} DATABASE_URL not set, using default SQLite database"
    export DATABASE_URL="sqlite:////app/data/produck.db"
fi

# Validate DATABASE_URL format
if [[ "$DATABASE_URL" != sqlite://* ]] && [[ "$DATABASE_URL" != postgresql://* ]]; then
    echo -e "${RED}[ERROR]${NC} DATABASE_URL has invalid format: $DATABASE_URL"
    echo -e "${YELLOW}[HINT]${NC} Valid formats:"
    echo -e "${YELLOW}[HINT]${NC}   SQLite: sqlite:////app/data/produck.db"
    echo -e "${YELLOW}[HINT]${NC}   PostgreSQL: postgresql://user:password@host:port/database"
    VALIDATION_FAILED=true
fi

# Check ENVIRONMENT
if [ -z "$ENVIRONMENT" ]; then
    echo -e "${YELLOW}[WARN]${NC} ENVIRONMENT not set, defaulting to 'development'"
    export ENVIRONMENT="development"
fi

if [ "$ENVIRONMENT" != "development" ] && [ "$ENVIRONMENT" != "production" ]; then
    echo -e "${YELLOW}[WARN]${NC} ENVIRONMENT has unexpected value: $ENVIRONMENT"
    echo -e "${YELLOW}[HINT]${NC} Valid values are: development, production"
fi

# Exit if validation failed
if [ "$VALIDATION_FAILED" = true ]; then
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  Configuration validation failed - cannot start           ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}[INFO]${NC} To fix these issues:"
    echo -e "  1. Copy .env.example to .env: ${YELLOW}cp .env.example .env${NC}"
    echo -e "  2. Edit .env and update the required variables"
    echo -e "  3. Restart the containers: ${YELLOW}docker-compose restart${NC}"
    echo ""
    exit 1
fi

echo -e "${GREEN}[✓]${NC} Environment variables validated"
echo -e "${GREEN}[✓]${NC} Environment: ${ENVIRONMENT}"
echo -e "${GREEN}[✓]${NC} Database: ${DATABASE_URL%%\?*}"  # Hide query params"

# ============================================================================
# Database Setup
# ============================================================================

echo -e "${BLUE}[INFO]${NC} Setting up database..."

# Ensure data directory exists
mkdir -p /app/data

# Check if database exists
if [ ! -f "/app/data/produck.db" ] && [[ "$DATABASE_URL" == *"sqlite"* ]]; then
    echo -e "${YELLOW}[WARN]${NC} Database not found, will initialize it"
    DB_INIT_REQUIRED=true
else
    echo -e "${GREEN}[✓]${NC} Database file exists or using PostgreSQL"
    DB_INIT_REQUIRED=false
fi

# Wait for PostgreSQL if using it
if [[ "$DATABASE_URL" == *"postgresql"* ]]; then
    echo -e "${BLUE}[INFO]${NC} Waiting for PostgreSQL to be ready..."
    
    # Extract host and port from DATABASE_URL
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    
    # Wait up to 30 seconds for PostgreSQL
    for i in {1..30}; do
        if pg_isready -h "$DB_HOST" -p "$DB_PORT" > /dev/null 2>&1; then
            echo -e "${GREEN}[✓]${NC} PostgreSQL is ready"
            break
        fi
        if [ $i -eq 30 ]; then
            echo -e "${RED}[ERROR]${NC} PostgreSQL is not ready after 30 seconds"
            exit 1
        fi
        echo -e "${YELLOW}[WAIT]${NC} Waiting for PostgreSQL... ($i/30)"
        sleep 1
    done
fi

# Run database migrations
echo -e "${BLUE}[INFO]${NC} Running database migrations..."
if alembic upgrade head; then
    echo -e "${GREEN}[✓]${NC} Database migrations completed"
else
    echo -e "${RED}[ERROR]${NC} Database migrations failed"
    echo -e "${YELLOW}[HINT]${NC} Check your DATABASE_URL configuration"
    exit 1
fi

# Initialize database if needed
if [ "$DB_INIT_REQUIRED" = true ]; then
    echo -e "${BLUE}[INFO]${NC} Initializing database with roles and admin user..."
    if python3 scripts/init_db.py; then
        echo -e "${GREEN}[✓]${NC} Database initialized successfully"
        echo -e "${BLUE}[INFO]${NC} Default admin user created"
    else
        echo -e "${RED}[ERROR]${NC} Database initialization failed"
        echo -e "${YELLOW}[HINT]${NC} Check the logs above for details"
        exit 1
    fi
else
    echo -e "${BLUE}[INFO]${NC} Database already initialized, skipping seed data"
fi

# ============================================================================
# Start Application
# ============================================================================

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         ProDuckt Backend Ready to Start                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Determine which server to use based on ENVIRONMENT
if [ "$ENVIRONMENT" = "production" ]; then
    echo -e "${BLUE}[INFO]${NC} Starting production server with Gunicorn..."
    echo -e "${BLUE}[INFO]${NC} Workers: 4, Worker class: uvicorn.workers.UvicornWorker"
    
    # Trap signals for graceful shutdown
    trap 'echo -e "${YELLOW}[WARN]${NC} Received shutdown signal, stopping gracefully..."; kill -TERM $PID' SIGTERM SIGINT
    
    # Start Gunicorn with Uvicorn workers
    exec gunicorn backend.main:app \
        --workers 4 \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind 0.0.0.0:8000 \
        --access-logfile - \
        --error-logfile - \
        --log-level info \
        --timeout 120 \
        --graceful-timeout 30 \
        --keep-alive 5
else
    echo -e "${BLUE}[INFO]${NC} Starting development server with Uvicorn..."
    echo -e "${BLUE}[INFO]${NC} Hot reload enabled"
    
    # Execute the command passed as arguments (typically uvicorn with --reload)
    exec "$@"
fi
