# Security Scanner CLI Usage Guide

## Overview

The ProDuckt Security Scanner is a command-line tool that analyzes your codebase for security vulnerabilities across five key security domains:

- **Authentication**: Password hashing, session management, cookie security
- **Authorization**: Access control, privilege escalation, multi-tenant isolation
- **Data Protection**: SQL injection, sensitive data exposure, input validation
- **API Security**: CORS configuration, rate limiting, XSS/CSRF protection
- **Infrastructure**: Hardcoded secrets, configuration security, logging

## Installation

Ensure PyYAML is installed:

```bash
pip install -r backend/requirements.txt
```

## Basic Usage

### Run a full security scan

```bash
python -m backend.security.cli
```

This will:
- Scan the current directory
- Run all security analyzers
- Generate a Markdown report
- Display a summary of findings

### Scan a specific directory

```bash
python -m backend.security.cli /path/to/project
```

### Specify output format

```bash
# Generate JSON report
python -m backend.security.cli -f json

# Generate HTML report
python -m backend.security.cli -f html

# Generate Markdown report (default)
python -m backend.security.cli -f markdown
```

### Specify output file

```bash
python -m backend.security.cli -o security-report.md
```

## Filtering Options

### Filter by severity

Only show findings at or above a certain severity level:

```bash
# Only show high and critical findings
python -m backend.security.cli --min-severity high

# Only show critical findings
python -m backend.security.cli --min-severity critical

# Show all findings (default)
python -m backend.security.cli --min-severity info
```

Severity levels (from lowest to highest):
- `info` - Informational findings
- `low` - Low severity issues
- `medium` - Medium severity issues
- `high` - High severity issues
- `critical` - Critical security vulnerabilities

### Filter by security category

Run only specific security analyzers:

```bash
# Only run authentication analyzer
python -m backend.security.cli -a authentication

# Run multiple specific analyzers
python -m backend.security.cli -a authentication authorization

# Alternative syntax using --categories
python -m backend.security.cli --categories data_protection api_security
```

Available analyzers:
- `authentication` - Authentication security checks
- `authorization` - Authorization and access control checks
- `data_protection` - Data security and privacy checks
- `api_security` - API-specific security checks
- `infrastructure` - Configuration and infrastructure checks
- `all` - Run all analyzers (default)

### Filter by file patterns

Include or exclude specific files:

```bash
# Only scan backend Python files
python -m backend.security.cli --include "backend/**/*.py"

# Exclude test files
python -m backend.security.cli --exclude "**/tests/**" "**/test_*.py"

# Combine include and exclude
python -m backend.security.cli \
  --include "backend/**/*.py" "frontend/src/**/*.js" \
  --exclude "**/tests/**" "**/node_modules/**"
```

## Configuration File

### Using a configuration file

Create a `.security-scan.yaml` file in your project root:

```yaml
include:
  - "backend/**/*.py"
  - "frontend/src/**/*.js"

exclude:
  - "**/tests/**"
  - "**/node_modules/**"

analyzers:
  - authentication
  - authorization
  - data_protection

severity:
  min_level: "medium"

output:
  format: "markdown"
  path: "security-report.md"

performance:
  max_workers: 4
  timeout: 300
  file_size_limit_mb: 10
```

The scanner will automatically detect and use this file:

```bash
python -m backend.security.cli
```

### Specify a custom configuration file

```bash
python -m backend.security.cli -c /path/to/config.yaml
```

### CLI overrides configuration file

Command-line arguments take precedence over configuration file settings:

```bash
# Use config file but override output format
python -m backend.security.cli -c config.yaml -f json

# Use config file but override severity filter
python -m backend.security.cli -c config.yaml --min-severity high
```

## Performance Options

### Adjust parallel workers

Control the number of parallel workers for scanning:

```bash
# Use 8 workers for faster scanning
python -m backend.security.cli -w 8

# Use 1 worker for sequential scanning
python -m backend.security.cli -w 1
```

Default: 4 workers

## Complete Example

Scan the backend directory, run only authentication and authorization checks, filter for high severity issues, and output to JSON:

```bash
python -m backend.security.cli backend \
  --analyzers authentication authorization \
  --min-severity high \
  --format json \
  --output backend-security.json \
  --exclude "**/tests/**" "**/venv/**" \
  --workers 8
```

## Exit Codes

The scanner returns different exit codes based on findings:

- `0` - Success, no critical or high severity findings
- `1` - Error occurred, or critical/high severity findings detected

This makes it suitable for CI/CD pipelines:

```bash
# Fail CI build if critical or high severity issues found
python -m backend.security.cli || exit 1
```

## Output Formats

### Markdown (default)

Human-readable report with:
- Executive summary
- Findings grouped by severity and category
- Code snippets and line numbers
- Remediation guidance

### JSON

Machine-readable format for integration with other tools:

```json
{
  "scan_id": "uuid",
  "scan_date": "2024-11-17T10:30:00",
  "total_findings": 15,
  "findings_by_severity": {
    "critical": 2,
    "high": 5,
    "medium": 8
  },
  "findings": [...]
}
```

### HTML

Styled HTML report with:
- Interactive navigation
- Syntax-highlighted code snippets
- Filterable findings
- Print-friendly layout

## Configuration File Reference

### Complete configuration example

```yaml
# File patterns to include
include:
  - "backend/**/*.py"
  - "frontend/src/**/*.js"
  - "frontend/src/**/*.jsx"

# File patterns to exclude
exclude:
  - "**/tests/**"
  - "**/test_*.py"
  - "**/__pycache__/**"
  - "**/venv/**"
  - "**/node_modules/**"

# Security analyzers to run
analyzers:
  - authentication
  - authorization
  - data_protection
  - api_security
  - infrastructure

# Severity filtering
severity:
  min_level: "medium"  # info, low, medium, high, critical

# Output configuration
output:
  format: "markdown"  # json, markdown, html
  path: "security-report.md"  # optional

# Performance settings
performance:
  max_workers: 4
  timeout: 300
  file_size_limit_mb: 10
```

## Tips and Best Practices

1. **Start with high severity**: Use `--min-severity high` to focus on critical issues first
2. **Use configuration files**: Store common settings in `.security-scan.yaml` for consistency
3. **Integrate with CI/CD**: Add the scanner to your CI pipeline to catch issues early
4. **Review regularly**: Run scans regularly, not just before releases
5. **Customize patterns**: Adjust include/exclude patterns to match your project structure
6. **Incremental fixes**: Address findings incrementally, starting with critical issues

## Troubleshooting

### Scanner runs slowly

- Reduce the number of workers: `-w 2`
- Exclude large directories: `--exclude "**/node_modules/**"`
- Reduce file size limit in config

### Too many false positives

- Increase minimum severity: `--min-severity medium`
- Run specific analyzers: `-a authentication authorization`
- Review and adjust patterns in configuration file

### Configuration file not found

- Ensure file is named `.security-scan.yaml` or `.security-scan.yml`
- Place file in project root or specify path with `-c`
- Check YAML syntax is valid

## Support

For issues or questions, refer to the main security scanner documentation in `backend/security/README.md`.
