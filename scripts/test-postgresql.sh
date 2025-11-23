#!/bin/bash
# ============================================================================
# PostgreSQL Configuration Test Script
# ============================================================================
# This script tests the PostgreSQL configuration for ProDuckt
# Tests: initialization, data persistence, and network isolation
# ============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Function to print test header
print_test_header() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  $1${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -e "${BLUE}[TEST $TESTS_TOTAL]${NC} $test_name"
    
    if eval "$test_command"; then
        echo -e "${GREEN}[✓ PASS]${NC} $test_name"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        return 0
    else
        echo -e "${RED}[✗ FAIL]${NC} $test_name"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        return 1
    fi
}

# Function to print test summary
print_summary() {
    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║  Test Summary${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Total Tests: $TESTS_TOTAL"
    echo -e "  ${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "  ${RED}Failed: $TESTS_FAILED${NC}"
    echo ""
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║  All PostgreSQL tests passed! ✓${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
        return 0
    else
        echo -e "${RED}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${RED}║  Some PostgreSQL tests failed ✗${NC}"
        echo -e "${RED}╚════════════════════════════════════════════════════════════╝${NC}"
        return 1
    fi
}

# ============================================================================
# Main Test Execution
# ============================================================================

print_test_header "PostgreSQL Configuration Test Suite"

echo -e "${BLUE}[INFO]${NC} This script will test PostgreSQL configuration"
echo -e "${BLUE}[INFO]${NC} Requirements tested: 4.4, 5.5, 8.4"
echo ""

# ============================================================================
# Pre-Test Setup
# ============================================================================

print_test_header "Pre-Test Setup"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}[WARN]${NC} .env file not found, creating from .env.example"
    cp .env.example .env
fi

# Backup current .env
echo -e "${BLUE}[INFO]${NC} Backing up current .env to .env.backup"
cp .env .env.backup

# Create PostgreSQL-specific .env
echo -e "${BLUE}[INFO]${NC} Configuring environment for PostgreSQL"
cat > .env.postgres << 'EOF'
# PostgreSQL Test Configuration
BUILD_TARGET=development
DATABASE_URL=postgresql://produck:testpassword123@db:5432/produck
POSTGRES_DB=produck
POSTGRES_USER=produck
POSTGRES_PASSWORD=testpassword123
SECRET_KEY=test-secret-key-for-postgresql-testing-32chars
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
ENVIRONMENT=development
LOG_LEVEL=INFO
HOST=0.0.0.0
PORT=8000
RELOAD=True
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
VITE_API_BASE_URL=http://localhost:8000
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_ORG_PER_MINUTE=1000
EOF

# Copy ANTHROPIC_API_KEY from original .env if it exists
if grep -q "ANTHROPIC_API_KEY=" .env.backup; then
    ANTHROPIC_KEY=$(grep "ANTHROPIC_API_KEY=" .env.backup | cut -d'=' -f2-)
    sed -i "s|\${ANTHROPIC_API_KEY}|$ANTHROPIC_KEY|g" .env.postgres
fi

cp .env.postgres .env

# Create PostgreSQL-enabled docker-compose override
echo -e "${BLUE}[INFO]${NC} Creating docker-compose.postgres.yml"
cat > docker-compose.postgres.yml << 'EOF'
version: '3.8'

services:
  backend:
    depends_on:
      db:
        condition: service_healthy
    environment:
      - DATABASE_URL=postgresql://produck:testpassword123@db:5432/produck

  db:
    image: postgres:15-alpine
    container_name: produck-db
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETGID
      - SETUID
      - DAC_OVERRIDE
    environment:
      - POSTGRES_DB=produck
      - POSTGRES_USER=produck
      - POSTGRES_PASSWORD=testpassword123
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U produck"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped
    networks:
      - produck-network
    # Note: No ports exposed to host for security (internal network only)
EOF

echo -e "${GREEN}[✓]${NC} Pre-test setup complete"

# ============================================================================
# Test 1: Clean Start with PostgreSQL
# ============================================================================

print_test_header "Test 1: Clean Start with PostgreSQL"

echo -e "${BLUE}[INFO]${NC} Stopping any running containers..."
docker-compose down -v > /dev/null 2>&1 || true

echo -e "${BLUE}[INFO]${NC} Starting services with PostgreSQL..."
docker-compose -f docker-compose.yml -f docker-compose.postgres.yml up -d db backend

echo -e "${BLUE}[INFO]${NC} Waiting for services to be healthy (max 120 seconds)..."
WAIT_TIME=0
MAX_WAIT=120

while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    BACKEND_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' produck-backend 2>/dev/null || echo "starting")
    DB_HEALTH=$(docker inspect --format='{{.State.Health.Status}}' produck-db 2>/dev/null || echo "starting")
    
    if [ "$BACKEND_HEALTH" = "healthy" ] && [ "$DB_HEALTH" = "healthy" ]; then
        echo -e "${GREEN}[✓]${NC} All services are healthy"
        break
    fi
    
    if [ $WAIT_TIME -ge $MAX_WAIT ]; then
        echo -e "${RED}[✗]${NC} Services did not become healthy in time"
        echo -e "${BLUE}[INFO]${NC} Backend health: $BACKEND_HEALTH"
        echo -e "${BLUE}[INFO]${NC} Database health: $DB_HEALTH"
        docker-compose logs
        exit 1
    fi
    
    echo -e "${YELLOW}[WAIT]${NC} Backend: $BACKEND_HEALTH, DB: $DB_HEALTH (${WAIT_TIME}s/${MAX_WAIT}s)"
    sleep 5
    WAIT_TIME=$((WAIT_TIME + 5))
done

run_test "PostgreSQL container is running" \
    "docker ps | grep -q produck-db"

run_test "Backend container is running" \
    "docker ps | grep -q produck-backend"

run_test "PostgreSQL is healthy" \
    "[ \"\$(docker inspect --format='{{.State.Health.Status}}' produck-db)\" = \"healthy\" ]"

run_test "Backend is healthy" \
    "[ \"\$(docker inspect --format='{{.State.Health.Status}}' produck-backend)\" = \"healthy\" ]"

# ============================================================================
# Test 2: Database Initialization
# ============================================================================

print_test_header "Test 2: Database Initialization"

run_test "Backend health endpoint responds" \
    "curl -f -s http://localhost:8000/health > /dev/null"

run_test "Database connection is working" \
    "curl -s http://localhost:8000/health | grep -q '\"database\"' && curl -s http://localhost:8000/health | grep -q '\"healthy\"'"

run_test "PostgreSQL has produck database" \
    "sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db psql -U produck -d produck -c 'SELECT 1' > /dev/null 2>&1"

run_test "Database tables were created" \
    "sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db psql -U produck -d produck -c '\dt' | grep -q 'users'"

run_test "Roles were seeded" \
    "sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db psql -U produck -d produck -c 'SELECT COUNT(*) FROM roles' | grep -q '[1-9]'"

run_test "Admin user was created" \
    "sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db psql -U produck -d produck -c 'SELECT COUNT(*) FROM users' | grep -q '[1-9]'"

# ============================================================================
# Test 3: Data Persistence
# ============================================================================

print_test_header "Test 3: Data Persistence"

echo -e "${BLUE}[INFO]${NC} Creating test data..."

# Create a test initiative via API
TEST_RESPONSE=$(curl -s -X POST http://localhost:8000/api/initiatives \
    -H "Content-Type: application/json" \
    -d '{
        "name": "PostgreSQL Test Initiative",
        "description": "Testing data persistence",
        "organization_id": 1
    }' 2>/dev/null || echo "")

if echo "$TEST_RESPONSE" | grep -q "id"; then
    INITIATIVE_ID=$(echo "$TEST_RESPONSE" | grep -o '"id":[0-9]*' | cut -d':' -f2)
    echo -e "${GREEN}[✓]${NC} Test initiative created with ID: $INITIATIVE_ID"
else
    echo -e "${YELLOW}[WARN]${NC} Could not create test initiative via API, using direct DB insert"
    
    # First, create an organization if it doesn't exist
    ORG_ID=$(sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db psql -U produck -d produck -t -c \
        "SELECT id FROM organizations LIMIT 1" | tr -d ' \n')
    
    if [ -z "$ORG_ID" ]; then
        echo -e "${BLUE}[INFO]${NC} Creating test organization..."
        sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db psql -U produck -d produck -c \
            "INSERT INTO organizations (id, name, created_at, updated_at) 
             VALUES (gen_random_uuid(), 'Test Organization', NOW(), NOW())" \
            > /dev/null 2>&1
        ORG_ID=$(sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db psql -U produck -d produck -t -c \
            "SELECT id FROM organizations LIMIT 1" | tr -d ' \n')
    fi
    
    # Now create the initiative
    sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db psql -U produck -d produck -c \
        "INSERT INTO initiatives (id, title, description, status, iteration_count, organization_id, created_at, updated_at) 
         VALUES (gen_random_uuid(), 'PostgreSQL Test Initiative', 'Testing data persistence', 'DRAFT', 0, '$ORG_ID', NOW(), NOW())" \
        > /dev/null 2>&1
    INITIATIVE_ID=$(sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db psql -U produck -d produck -t -c \
        "SELECT id FROM initiatives WHERE title='PostgreSQL Test Initiative' LIMIT 1" | tr -d ' \n')
    echo -e "${GREEN}[✓]${NC} Test initiative created with ID: $INITIATIVE_ID"
fi

run_test "Test data was inserted" \
    "sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db psql -U produck -d produck -c 'SELECT COUNT(*) FROM initiatives WHERE title='\''PostgreSQL Test Initiative'\''' | grep -q '1'"

echo -e "${BLUE}[INFO]${NC} Restarting backend container..."
sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml restart backend > /dev/null 2>&1

echo -e "${BLUE}[INFO]${NC} Waiting for backend to be healthy again..."
sleep 10

run_test "Backend is healthy after restart" \
    "[ \"\$(docker inspect --format='{{.State.Health.Status}}' produck-backend)\" = \"healthy\" ]"

run_test "Test data persisted after backend restart" \
    "sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db psql -U produck -d produck -c 'SELECT COUNT(*) FROM initiatives WHERE title='\''PostgreSQL Test Initiative'\''' | grep -q '1'"

echo -e "${BLUE}[INFO]${NC} Restarting database container..."
sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml restart db > /dev/null 2>&1

echo -e "${BLUE}[INFO]${NC} Waiting for database to be healthy again..."
sleep 20

# Wait for backend to reconnect
echo -e "${BLUE}[INFO]${NC} Waiting for backend to reconnect to database..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health | grep -q '"healthy"'; then
        break
    fi
    sleep 2
done

run_test "Database is healthy after restart" \
    "[ \"\$(docker inspect --format='{{.State.Health.Status}}' produck-db)\" = \"healthy\" ]"

run_test "Backend reconnected to database" \
    "curl -s http://localhost:8000/health | grep -q '\"database\"' && curl -s http://localhost:8000/health | grep -q '\"healthy\"'"

run_test "Test data persisted after database restart" \
    "sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db psql -U produck -d produck -c 'SELECT COUNT(*) FROM initiatives WHERE title='\''PostgreSQL Test Initiative'\''' | grep -q '1'"

# ============================================================================
# Test 4: Network Isolation
# ============================================================================

print_test_header "Test 4: Network Isolation"

run_test "PostgreSQL is NOT exposed on host port 5432" \
    "! netstat -tuln 2>/dev/null | grep -q ':5432' && ! ss -tuln 2>/dev/null | grep -q ':5432'"

run_test "PostgreSQL is NOT accessible from host" \
    "! timeout 2 bash -c 'cat < /dev/null > /dev/tcp/localhost/5432' 2>/dev/null"

run_test "Backend CAN connect to PostgreSQL via internal network" \
    "sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T backend python3 -c 'import psycopg2; conn = psycopg2.connect(\"postgresql://produck:testpassword123@db:5432/produck\"); conn.close(); print(\"OK\")' 2>/dev/null | grep -q 'OK'"

run_test "PostgreSQL container is on produck-network" \
    "docker inspect produck-db | grep -q 'produck-network'"

run_test "Backend container is on produck-network" \
    "docker inspect produck-backend | grep -q 'produck-network'"

# ============================================================================
# Test 5: Volume Persistence
# ============================================================================

print_test_header "Test 5: Volume Persistence"

run_test "postgres-data volume exists" \
    "docker volume ls | grep -q postgres-data"

run_test "postgres-data volume is mounted" \
    "docker inspect produck-db | grep -q '/var/lib/postgresql/data'"

# Get current data size
INITIAL_SIZE=$(sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db du -s /var/lib/postgresql/data | awk '{print $1}')
echo -e "${BLUE}[INFO]${NC} Initial data size: ${INITIAL_SIZE}KB"

# Stop containers but keep volumes
echo -e "${BLUE}[INFO]${NC} Stopping containers (keeping volumes)..."
sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml down

run_test "postgres-data volume still exists after stopping containers" \
    "docker volume ls | grep -q postgres-data"

# Start containers again
echo -e "${BLUE}[INFO]${NC} Starting containers again..."
sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml up -d db backend

echo -e "${BLUE}[INFO]${NC} Waiting for services to be healthy..."
sleep 20

run_test "Services are healthy after restart" \
    "[ \"\$(docker inspect --format='{{.State.Health.Status}}' produck-backend)\" = \"healthy\" ] && [ \"\$(docker inspect --format='{{.State.Health.Status}}' produck-db)\" = \"healthy\" ]"

run_test "Data still exists after full restart" \
    "sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml exec -T db psql -U produck -d produck -c 'SELECT COUNT(*) FROM initiatives WHERE title='\''PostgreSQL Test Initiative'\''' | grep -q '1'"

# ============================================================================
# Cleanup
# ============================================================================

print_test_header "Cleanup"

echo -e "${BLUE}[INFO]${NC} Stopping containers..."
sudo docker-compose -f docker-compose.yml -f docker-compose.postgres.yml down

echo -e "${BLUE}[INFO]${NC} Restoring original .env..."
mv .env.backup .env

echo -e "${BLUE}[INFO]${NC} Removing test files..."
rm -f .env.postgres docker-compose.postgres.yml

echo -e "${GREEN}[✓]${NC} Cleanup complete"

# Note: Not removing volumes to allow inspection if needed
echo -e "${YELLOW}[INFO]${NC} PostgreSQL volume 'postgres-data' was preserved"
echo -e "${YELLOW}[INFO]${NC} To remove it, run: docker volume rm postgres-data"

# ============================================================================
# Print Summary
# ============================================================================

print_summary
