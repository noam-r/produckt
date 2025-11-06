#!/bin/bash
# Development server startup script

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Starting ProDuckt Development Server...${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found. Please run 'python -m venv venv' first."
    exit 1
fi

# Activate virtual environment
echo -e "${GREEN}Activating virtual environment...${NC}"
source venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo -e "${GREEN}Creating .env file from template...${NC}"
    cat > .env << EOF
# Environment
ENVIRONMENT=development

# Security
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

# Database
DATABASE_URL=sqlite:///./produck.db

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Anthropic API
ANTHROPIC_API_KEY=your_api_key_here
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Redis (optional for POC)
REDIS_URL=redis://localhost:6379/0
EOF
    echo -e "${GREEN}Created .env file. Please update ANTHROPIC_API_KEY before running agents.${NC}"
fi

# Install dependencies if needed
echo -e "${GREEN}Checking dependencies...${NC}"
pip install -q --upgrade pip
pip install -q -e .

# Run database migrations
echo -e "${GREEN}Running database migrations...${NC}"
alembic upgrade head || echo "No migrations to run or migrations not set up yet."

# Start the development server
echo -e "${BLUE}Starting server on http://localhost:8000${NC}"
echo -e "${BLUE}API documentation available at http://localhost:8000/docs${NC}"
echo ""

uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
