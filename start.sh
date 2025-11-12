#!/bin/bash

###############################################################################
# ProDuckt Development Server Startup Script
# Validates requirements, dependencies, and configuration before starting
###############################################################################

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Log files
BACKEND_LOG="$PROJECT_ROOT/backend.log"
FRONTEND_LOG="$PROJECT_ROOT/frontend.log"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           ProDuckt Development Server Startup            ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

###############################################################################
# Helper Functions
###############################################################################

print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

###############################################################################
# Validation: System Requirements
###############################################################################

print_status "Checking system requirements..."

# Check Python
if ! check_command python3; then
    print_error "Python 3 is not installed"
    echo "  Install: sudo apt-get install python3 python3-pip python3-venv"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    print_error "Python 3.10+ required, found $PYTHON_VERSION"
    exit 1
fi
print_success "Python $PYTHON_VERSION"

# Check Node.js
if ! check_command node; then
    print_error "Node.js is not installed"
    echo "  Install with nvm: nvm install 20 && nvm use 20"
    exit 1
fi

NODE_VERSION=$(node --version | sed 's/v//')
NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)

if [ "$NODE_MAJOR" -lt 20 ]; then
    print_error "Node.js 20+ required, found v$NODE_VERSION"
    echo "  Upgrade: nvm install 20 && nvm use 20"
    exit 1
fi
print_success "Node.js v$NODE_VERSION"

# Check system libraries for WeasyPrint (Linux only)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    print_status "Checking system libraries for PDF generation..."
    MISSING_LIBS=()

    if ! ldconfig -p | grep -q libpango; then
        MISSING_LIBS+=("libpango-1.0-0")
    fi
    if ! ldconfig -p | grep -q libgdk_pixbuf; then
        MISSING_LIBS+=("libgdk-pixbuf2.0-0")
    fi

    if [ ${#MISSING_LIBS[@]} -gt 0 ]; then
        print_warning "Missing system libraries: ${MISSING_LIBS[*]}"
        echo "  Install: sudo apt-get install -y python3-dev libpango-1.0-0 libpangoft2-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info"
        read -p "  Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        print_success "System libraries installed"
    fi
fi

###############################################################################
# Validation: Environment Configuration
###############################################################################

print_status "Checking environment configuration..."

if [ ! -f .env ]; then
    print_error ".env file not found"
    echo "  Copy template: cp .env.example .env"
    echo "  Then edit .env and set your ANTHROPIC_API_KEY and SECRET_KEY"
    exit 1
fi
print_success ".env file exists"

# Check required environment variables
source .env 2>/dev/null || true

if [ -z "$SECRET_KEY" ] || [ "$SECRET_KEY" = "change-me-to-a-secure-32-char-minimum-key" ]; then
    print_error "SECRET_KEY not configured in .env"
    echo "  Generate one: openssl rand -hex 32"
    exit 1
fi
print_success "SECRET_KEY configured"

if [ -z "$ANTHROPIC_API_KEY" ] || [ "$ANTHROPIC_API_KEY" = "sk-ant-your-key-here" ]; then
    print_error "ANTHROPIC_API_KEY not configured in .env"
    echo "  Get your API key: https://console.anthropic.com/"
    exit 1
fi
print_success "ANTHROPIC_API_KEY configured"

###############################################################################
# Validation: Backend Dependencies
###############################################################################

print_status "Checking backend setup..."

if [ ! -d "backend/venv" ]; then
    print_error "Backend virtual environment not found"
    echo "  Create it: python3 -m venv backend/venv"
    echo "  Then run: source backend/venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi
print_success "Virtual environment exists"

# Activate virtual environment
source backend/venv/bin/activate

# Check if key packages are installed
MISSING_PACKAGES=()
python3 -c "import fastapi" 2>/dev/null || MISSING_PACKAGES+=("fastapi")
python3 -c "import anthropic" 2>/dev/null || MISSING_PACKAGES+=("anthropic")
python3 -c "import weasyprint" 2>/dev/null || MISSING_PACKAGES+=("weasyprint")

if [ ${#MISSING_PACKAGES[@]} -gt 0 ]; then
    print_error "Missing Python packages: ${MISSING_PACKAGES[*]}"
    echo "  Install: pip install -r requirements.txt"
    exit 1
fi
print_success "Backend dependencies installed"

###############################################################################
# Validation: Database
###############################################################################

print_status "Checking database..."

if [ ! -f "produck.db" ]; then
    print_warning "Database not found, will initialize it"

    # Run migrations
    print_status "Running database migrations..."
    alembic upgrade head || {
        print_error "Failed to run migrations"
        exit 1
    }
    print_success "Migrations complete"

    # Initialize database
    print_status "Initializing database with roles and admin user..."
    python3 scripts/init_db.py || {
        print_error "Failed to initialize database"
        exit 1
    }
    print_success "Database initialized"
else
    print_success "Database exists"

    # Check if roles table is populated
    ROLE_COUNT=$(python3 -c "
import sqlite3
conn = sqlite3.connect('produck.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM roles')
count = cursor.fetchone()[0]
conn.close()
print(count)
" 2>/dev/null || echo "0")

    if [ "$ROLE_COUNT" -eq 0 ]; then
        print_warning "Roles table is empty, initializing..."
        python3 scripts/init_db.py || {
            print_error "Failed to initialize roles"
            exit 1
        }
    else
        print_success "Database initialized ($ROLE_COUNT roles)"
    fi
fi

###############################################################################
# Validation: Frontend Dependencies
###############################################################################

print_status "Checking frontend setup..."

if [ ! -d "frontend/node_modules" ]; then
    print_error "Frontend dependencies not installed"
    echo "  Install: cd frontend && npm install"
    exit 1
fi
print_success "Frontend dependencies installed"

###############################################################################
# Check if ports are already in use
###############################################################################

print_status "Checking ports..."

if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    print_warning "Port 8000 already in use"
    echo "  Stop existing server or use a different port"
    exit 1
fi

if lsof -Pi :5173 -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    print_warning "Port 5173 already in use"
    echo "  Stop existing server or use a different port"
    exit 1
fi
print_success "Ports 8000 and 5173 available"

###############################################################################
# Start Servers
###############################################################################

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                   Starting Servers                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Create trap to cleanup on exit
cleanup() {
    echo ""
    print_status "Shutting down servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null || true
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null || true
    fi
    print_success "Servers stopped"
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
print_status "Starting backend server..."
source backend/venv/bin/activate
python3 -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000 > "$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    print_error "Backend failed to start. Check $BACKEND_LOG for details"
    tail -20 "$BACKEND_LOG"
    exit 1
fi
print_success "Backend server started (PID: $BACKEND_PID)"

# Start frontend
print_status "Starting frontend server..."
cd frontend
npm run dev > "$FRONTEND_LOG" 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
sleep 3

# Check if frontend is running
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    print_error "Frontend failed to start. Check $FRONTEND_LOG for details"
    tail -20 "$FRONTEND_LOG"
    kill $BACKEND_PID 2>/dev/null || true
    exit 1
fi
print_success "Frontend server started (PID: $FRONTEND_PID)"

###############################################################################
# Success
###############################################################################

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              ProDuckt is running!                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}Access URLs:${NC}"
echo -e "  Frontend:  ${GREEN}http://localhost:5173${NC}"
echo -e "  Backend:   ${GREEN}http://localhost:8000${NC}"
echo -e "  API Docs:  ${GREEN}http://localhost:8000/docs${NC}"
echo ""
echo -e "${BLUE}Default Admin Login:${NC}"
echo -e "  Email:     ${YELLOW}admin@produckt.local${NC}"
echo -e "  ${YELLOW}Note: You will be prompted to change password on first login${NC}"
echo ""
echo -e "${BLUE}Logs:${NC}"
echo -e "  Backend:   $BACKEND_LOG"
echo -e "  Frontend:  $FRONTEND_LOG"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop both servers${NC}"
echo ""

# Wait for processes
wait
