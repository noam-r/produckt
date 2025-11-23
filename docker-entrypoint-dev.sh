#!/bin/bash
# ============================================================================
# ProDuckt Backend Docker Entrypoint Script - DEVELOPMENT MODE
# ============================================================================
# This script runs before the main application starts in development mode
# It handles database migrations, initialization, and starts uvicorn with
# hot-reload enabled for rapid development
# ============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

echo -e "${MAGENTA}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${MAGENTA}║    ProDuckt Backend - DEVELOPMENT MODE Starting          ║${NC}"
echo -e "${MAGENTA}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================================
# Environment Validation
# ============================================================================

echo -e "${BLUE}[INFO]${NC} Validating environment configuration..."

VALIDATION_FAILED=false

# Check SECRET_KEY (more lenient in development)
if [ -z "$SECRET_KEY" ]; then
    echo -e "${YELLOW}[WARN]${NC} SECRET_KEY not set, using development default"
    echo -e "${YELLOW}[HINT]${NC} This is OK for development, but set a secure key for production"
    export SECRET_KEY="dev-secret-key-change-in-production"
elif [ "$SECRET_KEY" = "change-me-to-a-secure-32-char-minimum-key" ]; then
    echo -e "${YELLOW}[WARN]${NC} SECRET_KEY is using the default value"
    echo -e "${YELLOW}[HINT]${NC} This is OK for development, but generate a secure key for production"
    echo -e "${YELLOW}[HINT]${NC} Generate one with: openssl rand -hex 32"
fi

# Check ANTHROPIC_API_KEY (skip in CI/test environments)
if [ "$SKIP_API_KEY_VALIDATION" != "true" ]; then
    if [ -z "$ANTHROPIC_API_KEY" ]; then
        echo -e "${RED}[ERROR]${NC} ANTHROPIC_API_KEY environment variable is not set"
        echo -e "${YELLOW}[HINT]${NC} Add ANTHROPIC_API_KEY to your .env file"
        echo -e "${YELLOW}[HINT]${NC} Get your API key from: https://console.anthropic.com/"
        echo ""
        echo -e "${BLUE}[INFO]${NC} Steps to fix:"
        echo -e "  1. Go to https://console.anthropic.com/"
        echo -e "  2. Create an account or sign in"
        echo -e "  3. Generate an API key"
        echo -e "  4. Add it to your .env file: ${YELLOW}ANTHROPIC_API_KEY=sk-ant-...${NC}"
        echo -e "  5. Restart containers: ${YELLOW}docker-compose restart${NC}"
        echo ""
        VALIDATION_FAILED=true
    elif [ "$ANTHROPIC_API_KEY" = "sk-ant-your-key-here" ]; then
        echo -e "${RED}[ERROR]${NC} ANTHROPIC_API_KEY is still using the placeholder value"
        echo -e "${YELLOW}[HINT]${NC} Update ANTHROPIC_API_KEY in your .env file with your actual API key"
        echo -e "${YELLOW}[HINT]${NC} Get your API key from: https://console.anthropic.com/"
        VALIDATION_FAILED=true
    fi
else
    echo -e "${YELLOW}[INFO]${NC} Skipping ANTHROPIC_API_KEY validation (SKIP_API_KEY_VALIDATION=true)"
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

# Set development-specific logging
export LOG_LEVEL="${LOG_LEVEL:-DEBUG}"
export ENVIRONMENT="development"

# Exit if validation failed
if [ "$VALIDATION_FAILED" = true ]; then
    echo ""
    echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  Configuration validation failed - cannot start           ║${NC}"
    echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}[INFO]${NC} Quick fix:"
    echo -e "  1. Copy .env.example to .env: ${YELLOW}cp .env.example .env${NC}"
    echo -e "  2. Edit .env and set ANTHROPIC_API_KEY"
    echo -e "  3. Restart: ${YELLOW}docker-compose restart${NC}"
    echo ""
    exit 1
fi

echo -e "${GREEN}[✓]${NC} Environment: ${ENVIRONMENT}"
echo -e "${GREEN}[✓]${NC} Log Level: ${LOG_LEVEL}"
echo -e "${GREEN}[✓]${NC} Database: ${DATABASE_URL%%\?*}"  # Hide query params

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
        echo -e "${YELLOW}[INFO]${NC} Default admin credentials:"
        echo -e "  Email: admin@example.com"
        echo -e "  Password: admin123"
    else
        echo -e "${RED}[ERROR]${NC} Database initialization failed"
        exit 1
    fi
fi

# ============================================================================
# Development Mode Configuration
# ============================================================================

echo ""
echo -e "${MAGENTA}[DEV]${NC} Development mode features enabled:"
echo -e "  ${GREEN}✓${NC} Hot reload on code changes"
echo -e "  ${GREEN}✓${NC} Debug logging (LOG_LEVEL=DEBUG)"
echo -e "  ${GREEN}✓${NC} Detailed error messages"
echo -e "  ${GREEN}✓${NC} API documentation at http://localhost:8000/docs"
echo ""

# ============================================================================
# Start Application with Hot Reload
# ============================================================================

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║      ProDuckt Backend Ready - Development Mode            ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}[INFO]${NC} Starting uvicorn with hot-reload enabled..."
echo -e "${BLUE}[INFO]${NC} API will be available at: http://localhost:8000"
echo -e "${BLUE}[INFO]${NC} API docs available at: http://localhost:8000/docs"
echo -e "${BLUE}[INFO]${NC} Watching for file changes in /app/backend..."
echo ""

# Start uvicorn with hot-reload enabled
# --reload: Enable auto-reload on code changes
# --host 0.0.0.0: Bind to all interfaces (required for Docker)
# --port 8000: Listen on port 8000
# --log-level debug: Enable debug logging
exec uvicorn backend.main:app \
    --reload \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level debug
