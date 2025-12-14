#!/bin/bash
# ============================================================================
# Database Compatibility Checker
# ============================================================================
# Systematically checks for SQLite/PostgreSQL compatibility issues
# ============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Database Compatibility Checker (SQLite vs PostgreSQL)    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

ISSUES_FOUND=0

# Function to check for pattern
check_pattern() {
    local pattern="$1"
    local description="$2"
    local files="$3"
    
    echo -e "${BLUE}[CHECK]${NC} $description"
    
    results=$(grep -rn "$pattern" backend/ --include="*.py" --exclude-dir=venv --exclude-dir=__pycache__ 2>/dev/null || true)
    
    if [ -n "$results" ]; then
        echo -e "${RED}[FOUND]${NC} Potential compatibility issues:"
        echo "$results" | head -20
        ISSUES_FOUND=$((ISSUES_FOUND + 1))
        echo ""
    else
        echo -e "${GREEN}[OK]${NC} No issues found"
        echo ""
    fi
}

echo "Checking for SQLite-specific SQL functions..."
echo "=============================================="
echo ""

# Check for strftime (SQLite-specific date formatting)
check_pattern "func\.strftime" "SQLite strftime() function"

# Check for date() function with SQLite-specific modifiers
check_pattern "func\.date.*weekday\|func\.date.*start of" "SQLite date() with modifiers"

# Check for AUTOINCREMENT (SQLite uses this, PostgreSQL uses SERIAL)
check_pattern "AUTOINCREMENT" "AUTOINCREMENT keyword (use SERIAL in PostgreSQL)"

# Check for PRAGMA statements (SQLite-specific)
check_pattern "PRAGMA" "PRAGMA statements (SQLite-specific)"

# Check for || string concatenation without CAST
check_pattern "Column.*\|\|" "String concatenation with || (may need explicit CAST)"

# Check for GLOB operator (SQLite-specific)
check_pattern "\.glob\|GLOB " "GLOB operator (SQLite-specific, use LIKE or regex)"

# Check for REGEXP without proper setup
check_pattern "REGEXP" "REGEXP operator (needs extension in PostgreSQL)"

# Check for datetime() function
check_pattern "func\.datetime" "SQLite datetime() function"

# Check for julianday() function
check_pattern "func\.julianday" "SQLite julianday() function"

# Check for random() vs RANDOM()
check_pattern "func\.random\(\)" "random() function (case-sensitive in PostgreSQL)"

# Check for LIMIT with OFFSET syntax differences
check_pattern "LIMIT.*OFFSET.*," "LIMIT/OFFSET syntax (check for comma usage)"

# Check for BOOLEAN type usage
echo -e "${BLUE}[CHECK]${NC} Boolean type compatibility"
bool_results=$(grep -rn "Boolean()" backend/ --include="*.py" --exclude-dir=venv 2>/dev/null || true)
if [ -n "$bool_results" ]; then
    echo -e "${YELLOW}[INFO]${NC} Boolean columns found (verify 0/1 vs true/false handling)"
    echo "$bool_results" | head -10
    echo ""
else
    echo -e "${GREEN}[OK]${NC} No Boolean type issues"
    echo ""
fi

# Check for TEXT vs VARCHAR differences
echo -e "${BLUE}[CHECK]${NC} TEXT vs VARCHAR usage"
text_results=$(grep -rn "Column.*Text\|Column.*String" backend/models/ --include="*.py" 2>/dev/null | wc -l)
echo -e "${YELLOW}[INFO]${NC} Found $text_results text/string columns (verify length constraints)"
echo ""

# Check for JSON column usage
echo -e "${BLUE}[CHECK]${NC} JSON column compatibility"
json_results=$(grep -rn "Column.*JSON\|Column.*JSONB" backend/models/ --include="*.py" 2>/dev/null || true)
if [ -n "$json_results" ]; then
    echo -e "${YELLOW}[INFO]${NC} JSON columns found (SQLite stores as TEXT, PostgreSQL has native JSON)"
    echo "$json_results"
    echo ""
else
    echo -e "${GREEN}[OK]${NC} No JSON columns"
    echo ""
fi

# Check for ENUM usage
echo -e "${BLUE}[CHECK]${NC} ENUM type compatibility"
enum_results=$(grep -rn "Column.*Enum" backend/models/ --include="*.py" 2>/dev/null || true)
if [ -n "$enum_results" ]; then
    echo -e "${YELLOW}[INFO]${NC} ENUM columns found (PostgreSQL creates types, SQLite uses CHECK constraints)"
    echo "$enum_results" | head -10
    echo ""
else
    echo -e "${GREEN}[OK]${NC} No ENUM columns"
    echo ""
fi

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  Summary${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ $ISSUES_FOUND -eq 0 ]; then
    echo -e "${GREEN}✓ No critical compatibility issues found${NC}"
    exit 0
else
    echo -e "${RED}✗ Found $ISSUES_FOUND potential compatibility issues${NC}"
    echo -e "${YELLOW}Review the issues above and update code to be database-agnostic${NC}"
    exit 1
fi
