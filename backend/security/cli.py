"""Command-line interface for security scanner."""

import argparse
import sys
from pathlib import Path

from backend.security.scanner import SecurityScanner, ScanConfig
from backend.security.models.finding import Severity
from backend.security.utils.config_loader import ConfigLoader


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="ProDuckt Security Scanner - Analyze codebase for security vulnerabilities"
    )
    
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Path to project root (default: current directory)"
    )
    
    parser.add_argument(
        "-o", "--output",
        help="Output file path (default: auto-generated)"
    )
    
    parser.add_argument(
        "-f", "--format",
        choices=["json", "markdown", "html"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    
    parser.add_argument(
        "-a", "--analyzers",
        nargs="+",
        default=["all"],
        help="Analyzers to run: all, authentication, authorization, data_protection, api_security, infrastructure (default: all)"
    )
    
    parser.add_argument(
        "-s", "--min-severity",
        choices=["info", "low", "medium", "high", "critical"],
        default="info",
        help="Minimum severity level to report (default: info)"
    )
    
    parser.add_argument(
        "-w", "--workers",
        type=int,
        default=4,
        help="Number of parallel workers (default: 4)"
    )
    
    parser.add_argument(
        "--exclude",
        nargs="+",
        help="Additional exclude patterns"
    )
    
    parser.add_argument(
        "--include",
        nargs="+",
        help="Include file patterns (e.g., **/*.py, backend/**/*.py)"
    )
    
    parser.add_argument(
        "-c", "--config",
        help="Path to YAML configuration file (default: searches for .security-scan.yaml)"
    )
    
    parser.add_argument(
        "--categories",
        nargs="+",
        dest="analyzers",
        help="Alias for --analyzers: specify security categories to scan"
    )
    
    args = parser.parse_args()
    
    # Convert severity string to enum
    severity_map = {
        "info": Severity.INFO,
        "low": Severity.LOW,
        "medium": Severity.MEDIUM,
        "high": Severity.HIGH,
        "critical": Severity.CRITICAL,
    }
    
    # Load configuration from file if available
    try:
        file_config = ConfigLoader.load_config(args.config, args.path)
    except Exception as e:
        print(f"Error loading configuration file: {e}", file=sys.stderr)
        return 1
    
    # Start with file config or defaults
    if file_config:
        config = file_config
        print(f"Loaded configuration from file")
    else:
        config = ScanConfig()
    
    # Apply CLI overrides (CLI takes precedence over file config)
    cli_overrides = {}
    
    # Only override if explicitly provided (not default values)
    if args.analyzers != ["all"]:
        cli_overrides["analyzers"] = args.analyzers
        config.enabled_analyzers = args.analyzers
    
    if args.min_severity != "info":
        cli_overrides["min_severity"] = severity_map[args.min_severity]
        config.min_severity = severity_map[args.min_severity]
    
    if args.format != "markdown":
        cli_overrides["output_format"] = args.format
        config.output_format = args.format
    
    if args.output:
        cli_overrides["output_path"] = args.output
        config.output_path = args.output
    
    if args.workers != 4:
        cli_overrides["max_workers"] = args.workers
        config.max_workers = args.workers
    
    if args.exclude:
        cli_overrides["exclude"] = args.exclude
        config.exclude_patterns.extend(args.exclude)
    
    if args.include:
        cli_overrides["include"] = args.include
        config.include_patterns = args.include
    
    # Initialize scanner
    try:
        scanner = SecurityScanner(args.path, config)
    except Exception as e:
        print(f"Error initializing scanner: {e}", file=sys.stderr)
        return 1
    
    # Run scan
    print("=" * 60)
    print("ProDuckt Security Scanner")
    print("=" * 60)
    print()
    
    try:
        report = scanner.scan()
    except Exception as e:
        print(f"Error during scan: {e}", file=sys.stderr)
        return 1
    
    # Save report
    try:
        output_file = scanner.save_report(report)
        print()
        print("=" * 60)
        print(f"Report saved to: {output_file}")
        print("=" * 60)
    except Exception as e:
        print(f"Error saving report: {e}", file=sys.stderr)
        return 1
    
    # Print summary
    print()
    print("Summary:")
    print(f"  Total Findings: {report.total_findings}")
    print(f"  Files Scanned: {report.files_scanned}")
    print(f"  Duration: {report.scan_duration_seconds:.2f}s")
    print()
    print("Findings by Severity:")
    for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
        count = report.findings_by_severity.get(severity, 0)
        if count > 0:
            print(f"  {severity.value.upper()}: {count}")
    
    # Return non-zero exit code if critical or high severity findings
    critical_count = report.findings_by_severity.get(Severity.CRITICAL, 0)
    high_count = report.findings_by_severity.get(Severity.HIGH, 0)
    
    if critical_count > 0 or high_count > 0:
        print()
        print(f"⚠️  Found {critical_count} critical and {high_count} high severity issues")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
