#!/bin/bash
# Test runner script with various options

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo -e "${RED}Error: Virtual environment not found.${NC}"
    exit 1
fi

# Default values
COVERAGE=true
VERBOSE=false
PATTERN=""
MARKERS=""
FAILED_FIRST=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cov|--no-coverage)
            COVERAGE=false
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -k|--pattern)
            PATTERN="$2"
            shift 2
            ;;
        -m|--markers)
            MARKERS="$2"
            shift 2
            ;;
        --ff|--failed-first)
            FAILED_FIRST=true
            shift
            ;;
        -h|--help)
            echo "Usage: ./scripts/test.sh [options]"
            echo ""
            echo "Options:"
            echo "  --no-cov              Run tests without coverage"
            echo "  -v, --verbose         Verbose output"
            echo "  -k, --pattern <pat>   Run tests matching pattern"
            echo "  -m, --markers <mark>  Run tests with specific markers"
            echo "  --ff, --failed-first  Run failed tests first"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./scripts/test.sh                          # Run all tests with coverage"
            echo "  ./scripts/test.sh --no-cov                 # Run without coverage"
            echo "  ./scripts/test.sh -k auth                  # Run only auth tests"
            echo "  ./scripts/test.sh -m unit                  # Run only unit tests"
            echo "  ./scripts/test.sh --ff                     # Run previously failed tests first"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Run './scripts/test.sh --help' for usage information"
            exit 1
            ;;
    esac
done

# Build pytest command
PYTEST_CMD="python -m pytest tests/"

if [ "$VERBOSE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD -v"
fi

if [ "$COVERAGE" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --cov=backend --cov-report=term-missing --cov-report=html"
else
    PYTEST_CMD="$PYTEST_CMD --no-cov"
fi

if [ -n "$PATTERN" ]; then
    PYTEST_CMD="$PYTEST_CMD -k '$PATTERN'"
fi

if [ -n "$MARKERS" ]; then
    PYTEST_CMD="$PYTEST_CMD -m '$MARKERS'"
fi

if [ "$FAILED_FIRST" = true ]; then
    PYTEST_CMD="$PYTEST_CMD --ff"
fi

# Run tests
echo -e "${BLUE}Running ProDuckt Tests...${NC}"
echo -e "${BLUE}Command: $PYTEST_CMD${NC}"
echo ""

eval $PYTEST_CMD
TEST_EXIT_CODE=$?

# Report results
echo ""
if [ $TEST_EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    if [ "$COVERAGE" = true ]; then
        echo -e "${BLUE}Coverage report: htmlcov/index.html${NC}"
    fi
else
    echo -e "${RED}✗ Some tests failed${NC}"
fi

exit $TEST_EXIT_CODE
