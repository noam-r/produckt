#!/bin/bash
# Smoke test script to verify all Docker services are healthy

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"
MAX_RETRIES=30
RETRY_DELAY=2

echo -e "${BLUE}=== ProDuckt Docker Smoke Tests ===${NC}\n"

# Function to check if a URL is accessible
check_url() {
    local url=$1
    local expected_status=${2:-200}
    local description=$3
    
    echo -e "${YELLOW}Testing: ${description}${NC}"
    
    local response_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")
    
    if [ "$response_code" = "$expected_status" ]; then
        echo -e "${GREEN}✓ ${description} - OK (HTTP ${response_code})${NC}\n"
        return 0
    else
        echo -e "${RED}✗ ${description} - FAILED (HTTP ${response_code}, expected ${expected_status})${NC}\n"
        return 1
    fi
}

# Function to wait for a service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local retries=0
    
    echo -e "${YELLOW}Waiting for ${service_name} to be ready...${NC}"
    
    while [ $retries -lt $MAX_RETRIES ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ ${service_name} is ready${NC}\n"
            return 0
        fi
        
        retries=$((retries + 1))
        echo -e "  Attempt $retries/$MAX_RETRIES..."
        sleep $RETRY_DELAY
    done
    
    echo -e "${RED}✗ ${service_name} failed to start after $MAX_RETRIES attempts${NC}\n"
    return 1
}

# Function to check Docker container status
check_containers() {
    echo -e "${YELLOW}Checking Docker containers...${NC}"
    
    # Get list of running containers
    local containers=$(docker-compose ps --services 2>/dev/null || docker compose ps --services 2>/dev/null)
    
    if [ -z "$containers" ]; then
        echo -e "${RED}✗ No Docker containers found. Is docker-compose running?${NC}\n"
        return 1
    fi
    
    local all_healthy=true
    
    for service in $containers; do
        # Check if container is running
        local status=$(docker-compose ps "$service" 2>/dev/null | grep "$service" | awk '{print $4}' || docker compose ps "$service" 2>/dev/null | grep "$service" | awk '{print $4}')
        
        if echo "$status" | grep -q "Up"; then
            echo -e "${GREEN}✓ $service is running${NC}"
        else
            echo -e "${RED}✗ $service is not running (status: $status)${NC}"
            all_healthy=false
        fi
    done
    
    echo ""
    
    if [ "$all_healthy" = true ]; then
        return 0
    else
        return 1
    fi
}

# Function to check container health status
check_health_status() {
    echo -e "${YELLOW}Checking container health status...${NC}"
    
    local all_healthy=true
    
    # Check backend health
    local backend_health=$(docker inspect --format='{{.State.Health.Status}}' $(docker-compose ps -q backend 2>/dev/null || docker compose ps -q backend 2>/dev/null) 2>/dev/null || echo "none")
    
    if [ "$backend_health" = "healthy" ] || [ "$backend_health" = "none" ]; then
        echo -e "${GREEN}✓ Backend health status: ${backend_health}${NC}"
    else
        echo -e "${RED}✗ Backend health status: ${backend_health}${NC}"
        all_healthy=false
    fi
    
    # Check frontend health
    local frontend_health=$(docker inspect --format='{{.State.Health.Status}}' $(docker-compose ps -q frontend 2>/dev/null || docker compose ps -q frontend 2>/dev/null) 2>/dev/null || echo "none")
    
    if [ "$frontend_health" = "healthy" ] || [ "$frontend_health" = "none" ]; then
        echo -e "${GREEN}✓ Frontend health status: ${frontend_health}${NC}"
    else
        echo -e "${RED}✗ Frontend health status: ${frontend_health}${NC}"
        all_healthy=false
    fi
    
    echo ""
    
    if [ "$all_healthy" = true ]; then
        return 0
    else
        return 1
    fi
}

# Function to test backend health endpoint
test_backend_health() {
    echo -e "${YELLOW}Testing backend health endpoint...${NC}"
    
    local response=$(curl -s "${BACKEND_URL}/health")
    local status_code=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/health")
    
    if [ "$status_code" = "200" ]; then
        echo -e "${GREEN}✓ Backend health endpoint returned 200${NC}"
        echo -e "  Response: $response\n"
        
        # Check if response contains expected fields
        if echo "$response" | grep -q "status"; then
            echo -e "${GREEN}✓ Health response contains status field${NC}\n"
            return 0
        else
            echo -e "${YELLOW}⚠ Health response missing expected fields${NC}\n"
            return 0
        fi
    else
        echo -e "${RED}✗ Backend health endpoint failed (HTTP ${status_code})${NC}\n"
        return 1
    fi
}

# Function to test frontend
test_frontend() {
    echo -e "${YELLOW}Testing frontend...${NC}"
    
    local response=$(curl -s "${FRONTEND_URL}")
    local status_code=$(curl -s -o /dev/null -w "%{http_code}" "${FRONTEND_URL}")
    
    if [ "$status_code" = "200" ]; then
        echo -e "${GREEN}✓ Frontend returned 200${NC}"
        
        # Check if response contains HTML
        if echo "$response" | grep -q "<html"; then
            echo -e "${GREEN}✓ Frontend serves HTML content${NC}\n"
            return 0
        else
            echo -e "${YELLOW}⚠ Frontend response doesn't appear to be HTML${NC}\n"
            return 0
        fi
    else
        echo -e "${RED}✗ Frontend failed (HTTP ${status_code})${NC}\n"
        return 1
    fi
}

# Function to test database connectivity
test_database() {
    echo -e "${YELLOW}Testing database connectivity through backend...${NC}"
    
    # Try to access an endpoint that requires database
    local status_code=$(curl -s -o /dev/null -w "%{http_code}" "${BACKEND_URL}/api/initiatives" -H "Content-Type: application/json")
    
    # 401 or 200 means database is accessible (401 = not authenticated, which is fine)
    if [ "$status_code" = "200" ] || [ "$status_code" = "401" ]; then
        echo -e "${GREEN}✓ Database is accessible through backend${NC}\n"
        return 0
    else
        echo -e "${RED}✗ Database connectivity test failed (HTTP ${status_code})${NC}\n"
        return 1
    fi
}

# Main test execution
main() {
    local failed_tests=0
    
    # Check if Docker containers are running
    if ! check_containers; then
        echo -e "${RED}Container check failed. Exiting.${NC}"
        exit 1
    fi
    
    # Wait for services to be ready
    if ! wait_for_service "${BACKEND_URL}/health" "Backend"; then
        failed_tests=$((failed_tests + 1))
    fi
    
    if ! wait_for_service "${FRONTEND_URL}" "Frontend"; then
        failed_tests=$((failed_tests + 1))
    fi
    
    # Run health status checks
    if ! check_health_status; then
        failed_tests=$((failed_tests + 1))
    fi
    
    # Run functional tests
    if ! test_backend_health; then
        failed_tests=$((failed_tests + 1))
    fi
    
    if ! test_frontend; then
        failed_tests=$((failed_tests + 1))
    fi
    
    if ! test_database; then
        failed_tests=$((failed_tests + 1))
    fi
    
    # Summary
    echo -e "${BLUE}=== Test Summary ===${NC}"
    if [ $failed_tests -eq 0 ]; then
        echo -e "${GREEN}All smoke tests passed! ✓${NC}"
        exit 0
    else
        echo -e "${RED}${failed_tests} test(s) failed ✗${NC}"
        echo -e "\n${YELLOW}Troubleshooting tips:${NC}"
        echo -e "  - Check logs: docker-compose logs"
        echo -e "  - Check container status: docker-compose ps"
        echo -e "  - Restart services: docker-compose restart"
        exit 1
    fi
}

# Run main function
main
