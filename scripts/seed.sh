#!/bin/bash
# Database seeding script wrapper

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}ProDuckt Database Seeding${NC}"
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found."
    exit 1
fi

# Check for --force flag
FORCE=false
if [ "$1" == "--force" ]; then
    FORCE=true
    echo -e "${YELLOW}Force mode: Will overwrite existing data${NC}"
fi

# Run the seeding script
python backend/scripts/seed_db.py

echo ""
echo -e "${GREEN}Seeding complete!${NC}"
