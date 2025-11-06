#!/bin/bash
# Database migration script

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found."
    exit 1
fi

# Parse command line arguments
COMMAND=${1:-upgrade}
REVISION=${2:-head}

case $COMMAND in
    "init")
        echo -e "${BLUE}Initializing Alembic...${NC}"
        alembic init alembic
        echo -e "${GREEN}Alembic initialized. Please update alembic.ini and alembic/env.py${NC}"
        ;;

    "create"|"revision")
        if [ -z "$2" ]; then
            echo "Error: Migration message required"
            echo "Usage: ./scripts/migrate.sh create 'migration message'"
            exit 1
        fi
        MESSAGE=$2
        echo -e "${BLUE}Creating new migration: ${MESSAGE}${NC}"
        alembic revision --autogenerate -m "$MESSAGE"
        echo -e "${GREEN}Migration created successfully${NC}"
        ;;

    "upgrade")
        echo -e "${BLUE}Running migrations (upgrade to ${REVISION})...${NC}"
        alembic upgrade $REVISION
        echo -e "${GREEN}Migrations completed successfully${NC}"
        ;;

    "downgrade")
        echo -e "${YELLOW}Downgrading database (to ${REVISION})...${NC}"
        alembic downgrade $REVISION
        echo -e "${GREEN}Downgrade completed${NC}"
        ;;

    "current")
        echo -e "${BLUE}Current database version:${NC}"
        alembic current
        ;;

    "history")
        echo -e "${BLUE}Migration history:${NC}"
        alembic history
        ;;

    "heads")
        echo -e "${BLUE}Current heads:${NC}"
        alembic heads
        ;;

    "stamp")
        if [ -z "$2" ]; then
            echo "Error: Revision required"
            echo "Usage: ./scripts/migrate.sh stamp <revision>"
            exit 1
        fi
        echo -e "${BLUE}Stamping database to revision: ${REVISION}${NC}"
        alembic stamp $REVISION
        echo -e "${GREEN}Database stamped${NC}"
        ;;

    *)
        echo "Usage: ./scripts/migrate.sh [command] [args]"
        echo ""
        echo "Commands:"
        echo "  init                    - Initialize Alembic"
        echo "  create 'message'        - Create new migration"
        echo "  upgrade [revision]      - Apply migrations (default: head)"
        echo "  downgrade [revision]    - Revert migrations (default: -1)"
        echo "  current                 - Show current revision"
        echo "  history                 - Show migration history"
        echo "  heads                   - Show current heads"
        echo "  stamp <revision>        - Stamp database with revision"
        exit 1
        ;;
esac
