# ProDuckt Security Scanner

A comprehensive security analysis tool for the ProDuckt application that automatically scans code for vulnerabilities across authentication, authorization, data protection, API security, and infrastructure layers.

## Features

- **Multi-Category Analysis**: Covers 5 key security domains
  - Authentication (password hashing, session management, brute force protection)
  - Authorization (access control, privilege escalation, multi-tenant isolation)
  - Data Protection (SQL injection, sensitive data exposure, input validation)
  - API Security (CORS, rate limiting, XSS, CSRF)
  - Infrastructure (hardcoded secrets, configuration issues, logging security)

- **Parallel Execution**: Fast scanning with configurable worker threads
- **Multiple Output Formats**: JSON, Markdown, and HTML reports
- **Severity-Based Prioritization**: OWASP risk methodology for consistent ratings
- **Actionable Remediation**: Specific fix steps with code examples
- **Deduplication**: Intelligent finding aggregation to reduce noise

## Installation

The security scanner is part of the ProDuckt backend. No additional installation required.

## Usage

### Command Line Interface

Basic usage:
```bash
python -m backend.security.cli [path] [options]
```

### Examples

Scan entire project with default settings:
```bash
python -m backend.security.cli .
```

Scan specific directory with custom output:
```bash
python -m backend.security.cli backend/auth -o auth_security_report.md
```

Generate JSON report with only high/critical findings:
```bash
python -m backend.security.cli . -f json -s high -o security_report.json
```

Run specific analyzers:
```bash
python -m backend.security.cli . -a authentication authorization
```

Scan with custom patterns:
```bash
python -m backend.security.cli . --include "**/*.py" --exclude "**/migrations/**"
```

### CLI Options

- `path`: Path to project root (default: current directory)
- `-o, --output`: Output file path (default: auto-generated)
- `-f, --format`: Output format - json, markdown, html (default: markdown)
- `-a, --analyzers`: Specific analyzers to run (default: all)
- `-s, --min-severity`: Minimum severity - info, low, medium, high, critical (default: info)
- `-w, --workers`: Number of parallel workers (default: 4)
- `--exclude`: Additional exclude patterns
- `--include`: Include patterns (default: **/*.py)

### Programmatic Usage

```python
from backend.security import SecurityScanner, ScanConfig
from backend.security.models.finding import Severity

# Create configuration
config = ScanConfig(
    enabled_analyzers=["all"],
    min_severity=Severity.MEDIUM,
    output_format="markdown",
    max_workers=4,
)

# Initialize scanner
scanner = SecurityScanner(".", config)

# Run scan
report = scanner.scan()

# Save report
scanner.save_report(report, "security_report.md")

# Access findings programmatically
for finding in report.findings:
    print(f"{finding.severity.value}: {finding.title}")
    print(f"  File: {finding.file_path}:{finding.line_number}")
    print(f"  {finding.description}")
```

### Scan Specific Categories

```python
# Run only authentication and authorization analyzers
report = scanner.scan_specific(["authentication", "authorization"])
```

## Report Formats

### Markdown Report

Human-readable report with:
- Executive summary with statistics
- Findings grouped by severity
- Code snippets and remediation guidance
- References to OWASP and CWE standards

### JSON Report

Machine-readable format for:
- CI/CD integration
- Automated processing
- Trend analysis
- Custom reporting tools

### HTML Report

Styled web report with:
- Color-coded severity badges
- Collapsible sections
- Syntax-highlighted code
- Clickable references

## Security Categories

### Authentication
- Weak password hashing algorithms
- Insufficient bcrypt rounds
- Insecure session storage
- Missing session expiration
- Weak password policies
- Missing brute force protection
- Insecure cookie configurations

### Authorization
- Missing authorization checks on endpoints
- Privilege escalation vulnerabilities
- Multi-tenant data isolation issues
- Missing role validation
- Horizontal privilege escalation risks

### Data Protection
- SQL injection vulnerabilities
- Sensitive data exposure in responses/logs
- Missing input validation
- Unencrypted sensitive data
- PII handling issues

### API Security
- CORS misconfigurations
- Missing rate limiting
- XSS vulnerabilities
- Missing CSRF protection
- File upload security issues

### Infrastructure
- Hardcoded secrets
- Dependency vulnerabilities
- Information disclosure in errors
- Sensitive data in logs
- Insecure production settings

## Severity Levels

Findings are classified using OWASP risk methodology:

- **CRITICAL**: Immediate action required - exploitable vulnerabilities with severe impact
- **HIGH**: Should be fixed soon - significant security risks
- **MEDIUM**: Should be addressed - moderate security concerns
- **LOW**: Minor issues - low-impact vulnerabilities
- **INFO**: Informational only - security best practices

## Configuration

### Default Exclude Patterns

The scanner automatically excludes:
- `**/tests/**` - Test files
- `**/test_**` - Test files
- `**/__pycache__/**` - Python cache
- `**/*.pyc` - Compiled Python files
- `**/venv/**` - Virtual environments
- `**/node_modules/**` - Node modules
- `**/alembic/versions/**` - Database migrations
- `**/.git/**` - Git directory

### Custom Configuration

Create a `.security-scan.yaml` file in your project root:

```yaml
include:
  - "backend/**/*.py"
  - "scripts/**/*.py"

exclude:
  - "**/tests/**"
  - "**/migrations/**"

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
```

## CI/CD Integration

### GitHub Actions

```yaml
name: Security Scan

on: [push, pull_request]

jobs:
  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run security scan
        run: |
          python -m backend.security.cli . -f json -s high -o security-report.json
      - name: Upload report
        uses: actions/upload-artifact@v2
        with:
          name: security-report
          path: security-report.json
```

### Exit Codes

The CLI returns:
- `0`: Success (no critical/high findings)
- `1`: Critical or high severity findings detected

Use this for CI/CD pipeline gating.

## Extending the Scanner

### Adding Custom Analyzers

1. Create a new analyzer class inheriting from `BaseAnalyzer`:

```python
from backend.security.analyzers.base import BaseAnalyzer
from backend.security.models.finding import Finding

class CustomAnalyzer(BaseAnalyzer):
    def get_category(self) -> str:
        return "custom_category"
    
    def analyze(self, file_path: str, content: str) -> List[Finding]:
        findings = []
        # Your analysis logic here
        return findings
```

2. Register it in `scanner.py`:

```python
from backend.security.analyzers.custom import CustomAnalyzer

available_analyzers = {
    # ... existing analyzers
    "custom": CustomAnalyzer,
}
```

### Adding Custom Remediation Templates

```python
from backend.security.utils.remediation import RemediationGuide

RemediationGuide.add_custom_remediation(
    vulnerability_type="custom_vuln",
    description="Description of the vulnerability",
    remediation="Steps to fix the issue",
    code_example="# Example fix code",
    cwe_id="CWE-XXX",
    owasp_category="A0X:2021 - Category",
    references=["https://example.com/reference"],
)
```

## Performance

Expected scan times:
- Small project (<100 files): < 10 seconds
- Medium project (100-500 files): < 30 seconds
- Large project (500+ files): < 2 minutes

Optimize performance by:
- Increasing worker count: `-w 8`
- Excluding unnecessary directories: `--exclude "**/migrations/**"`
- Running specific analyzers: `-a authentication authorization`

## Troubleshooting

### "Error reading file" messages

These are usually harmless warnings for binary files (.pyc, .pyo). The scanner will skip them automatically.

### High memory usage

Reduce the number of workers: `-w 2`

### Slow scans

- Exclude large directories with `--exclude`
- Run specific analyzers instead of all
- Increase file size limit in config

## Contributing

To add new security checks:

1. Identify the vulnerability pattern
2. Add detection logic to appropriate analyzer
3. Include remediation guidance with code examples
4. Add test cases with vulnerable and secure code
5. Update documentation

## References

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [OWASP Cheat Sheet Series](https://cheatsheetseries.owasp.org/)
- [CWE - Common Weakness Enumeration](https://cwe.mitre.org/)
- [NIST Cybersecurity Framework](https://www.nist.gov/cyberframework)

## License

Part of the ProDuckt application. See main project LICENSE file.
