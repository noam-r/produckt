"""Main security scanner orchestrator."""

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from backend.security.models.finding import Finding, Severity
from backend.security.models.report import SecurityReport
from backend.security.analyzers.base import BaseAnalyzer
from backend.security.analyzers.authentication import AuthenticationAnalyzer
from backend.security.analyzers.authorization import AuthorizationAnalyzer
from backend.security.analyzers.data_protection import DataProtectionAnalyzer
from backend.security.analyzers.api_security import APISecurityAnalyzer
from backend.security.analyzers.infrastructure import InfrastructureAnalyzer


@dataclass
class ScanConfig:
    """Configuration for security scan."""
    
    # Scope
    include_patterns: List[str] = field(default_factory=lambda: ["**/*.py"])
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "**/tests/**", 
        "**/test_**", 
        "**/__pycache__/**",
        "**/*.pyc",
        "**/*.pyo",
        "**/venv/**", 
        "**/node_modules/**",
        "**/alembic/versions/**",
        "**/.git/**",
    ])
    
    # Analyzers
    enabled_analyzers: List[str] = field(default_factory=lambda: ["all"])
    
    # Severity filtering
    min_severity: Severity = Severity.INFO
    
    # Output
    output_format: str = "markdown"  # json, markdown, html
    output_path: Optional[str] = None
    
    # Performance
    max_workers: int = 4
    file_size_limit_mb: int = 10
    timeout_seconds: int = 300


class SecurityScanner:
    """
    Main security scanner orchestrator.
    
    Coordinates the execution of all security analyzers and aggregates results
    into a comprehensive security report.
    """
    
    def __init__(self, root_path: str, config: Optional[ScanConfig] = None):
        """
        Initialize scanner with project root and configuration.
        
        Args:
            root_path: Root directory of the project to scan
            config: Scan configuration (uses defaults if not provided)
        """
        self.root_path = Path(root_path).resolve()
        self.config = config or ScanConfig()
        self.analyzers: List[BaseAnalyzer] = []
        self._load_analyzers()
    
    def _load_analyzers(self) -> None:
        """Load and register all security analyzers."""
        # Available analyzer classes
        available_analyzers = {
            "authentication": AuthenticationAnalyzer,
            "authorization": AuthorizationAnalyzer,
            "data_protection": DataProtectionAnalyzer,
            "api_security": APISecurityAnalyzer,
            "infrastructure": InfrastructureAnalyzer,
        }
        
        # Determine which analyzers to load
        if "all" in self.config.enabled_analyzers:
            analyzers_to_load = available_analyzers.keys()
        else:
            analyzers_to_load = [
                name for name in self.config.enabled_analyzers 
                if name in available_analyzers
            ]
        
        # Instantiate analyzers
        for name in analyzers_to_load:
            analyzer_class = available_analyzers[name]
            try:
                analyzer = analyzer_class()
                self.analyzers.append(analyzer)
            except Exception as e:
                print(f"Warning: Failed to load analyzer '{name}': {e}")
    
    def _discover_files(self) -> List[Path]:
        """
        Discover files to scan based on include/exclude patterns.
        
        Returns:
            List of file paths to analyze
        """
        files_to_scan = []
        
        # Walk through the directory tree
        for root, dirs, files in os.walk(self.root_path):
            # Filter out excluded directories
            dirs[:] = [
                d for d in dirs 
                if not self._is_excluded(os.path.join(root, d))
            ]
            
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(self.root_path)
                
                # Check if file matches include patterns and not excluded
                if self._should_scan_file(relative_path):
                    # Check file size limit
                    try:
                        file_size_mb = file_path.stat().st_size / (1024 * 1024)
                        if file_size_mb <= self.config.file_size_limit_mb:
                            files_to_scan.append(file_path)
                        else:
                            print(f"Skipping {relative_path}: exceeds size limit")
                    except Exception as e:
                        print(f"Warning: Could not check size of {relative_path}: {e}")
        
        return files_to_scan
    
    def _should_scan_file(self, relative_path: Path) -> bool:
        """
        Check if a file should be scanned based on patterns.
        
        Args:
            relative_path: Path relative to project root
            
        Returns:
            True if file should be scanned
        """
        path_str = str(relative_path)
        
        # Check if excluded
        if self._is_excluded(path_str):
            return False
        
        # Check if matches include patterns
        for pattern in self.config.include_patterns:
            if self._matches_pattern(path_str, pattern):
                return True
        
        return False
    
    def _is_excluded(self, path_str: str) -> bool:
        """Check if path matches any exclude pattern."""
        for pattern in self.config.exclude_patterns:
            if self._matches_pattern(path_str, pattern):
                return True
        return False
    
    def _matches_pattern(self, path_str: str, pattern: str) -> bool:
        """
        Simple pattern matching for file paths.
        
        Supports:
        - **/ for recursive directory matching
        - * for wildcard matching
        """
        # Convert to Path for consistent comparison
        path_str = path_str.replace('\\', '/')
        pattern = pattern.replace('\\', '/')
        
        # Handle ** recursive pattern
        if '**' in pattern:
            pattern_parts = pattern.split('**/')
            if len(pattern_parts) == 2:
                prefix, suffix = pattern_parts
                # Check if path contains the pattern
                if prefix and not path_str.startswith(prefix):
                    return False
                if suffix:
                    suffix = suffix.rstrip('/')
                    if suffix.startswith('*'):
                        # Wildcard pattern
                        return path_str.endswith(suffix[1:]) or suffix[1:] in path_str
                    else:
                        return suffix in path_str
                return True
        
        # Handle simple wildcard
        if '*' in pattern:
            if pattern.startswith('*'):
                return path_str.endswith(pattern[1:])
            elif pattern.endswith('*'):
                return path_str.startswith(pattern[:-1])
            else:
                # Pattern in the middle
                parts = pattern.split('*')
                return path_str.startswith(parts[0]) and path_str.endswith(parts[1])
        
        # Exact match
        return path_str == pattern or path_str.endswith('/' + pattern)
    
    def _analyze_file(self, file_path: Path) -> List[Finding]:
        """
        Analyze a single file with all applicable analyzers.
        
        Args:
            file_path: Path to file to analyze
            
        Returns:
            List of findings from all analyzers
        """
        findings = []
        relative_path = str(file_path.relative_to(self.root_path))
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Run each analyzer
            for analyzer in self.analyzers:
                if analyzer.should_analyze_file(relative_path):
                    try:
                        analyzer_findings = analyzer.analyze(relative_path, content)
                        findings.extend(analyzer_findings)
                    except Exception as e:
                        print(f"Error in {analyzer.get_name()} analyzing {relative_path}: {e}")
        
        except Exception as e:
            print(f"Error reading file {relative_path}: {e}")
        
        return findings
    
    def scan(self) -> SecurityReport:
        """
        Execute all analyzers and return comprehensive report.
        
        Returns:
            SecurityReport with all findings
        """
        start_time = time.time()
        scan_id = str(uuid.uuid4())
        
        print(f"Starting security scan (ID: {scan_id})")
        print(f"Root path: {self.root_path}")
        print(f"Loaded analyzers: {[a.get_name() for a in self.analyzers]}")
        
        # Discover files to scan
        files_to_scan = self._discover_files()
        print(f"Found {len(files_to_scan)} files to scan")
        
        # Analyze files in parallel
        all_findings = []
        with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
            future_to_file = {
                executor.submit(self._analyze_file, file_path): file_path
                for file_path in files_to_scan
            }
            
            for future in as_completed(future_to_file):
                file_path = future_to_file[future]
                try:
                    findings = future.result()
                    all_findings.extend(findings)
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
        
        # Deduplicate findings
        deduplicated_findings = self._deduplicate_findings(all_findings)
        
        # Filter by minimum severity
        filtered_findings = [
            f for f in deduplicated_findings 
            if self._severity_meets_minimum(f.severity)
        ]
        
        # Group and sort findings
        grouped_findings = self._group_findings(filtered_findings)
        
        # Calculate statistics
        findings_by_severity = {}
        findings_by_category = {}
        
        for finding in grouped_findings:
            # Count by severity
            findings_by_severity[finding.severity] = \
                findings_by_severity.get(finding.severity, 0) + 1
            
            # Count by category
            findings_by_category[finding.category] = \
                findings_by_category.get(finding.category, 0) + 1
        
        # Create report
        scan_duration = time.time() - start_time
        report = SecurityReport(
            scan_id=scan_id,
            scan_date=datetime.now(),
            project_path=str(self.root_path),
            total_findings=len(grouped_findings),
            findings_by_severity=findings_by_severity,
            findings_by_category=findings_by_category,
            findings=grouped_findings,
            analyzers_run=[a.get_name() for a in self.analyzers],
            files_scanned=len(files_to_scan),
            scan_duration_seconds=scan_duration,
        )
        
        print(f"Scan complete: {len(grouped_findings)} findings in {scan_duration:.2f}s")
        
        return report
    
    def _deduplicate_findings(self, findings: List[Finding]) -> List[Finding]:
        """
        Deduplicate findings based on key attributes.
        
        Two findings are considered duplicates if they have the same:
        - Category
        - Title
        - File path
        - Line number (if present)
        
        Args:
            findings: List of findings to deduplicate
            
        Returns:
            Deduplicated list of findings
        """
        seen = set()
        deduplicated = []
        
        for finding in findings:
            # Create a unique key for this finding
            key = (
                finding.category,
                finding.title,
                finding.file_path,
                finding.line_number,
            )
            
            if key not in seen:
                seen.add(key)
                deduplicated.append(finding)
        
        return deduplicated
    
    def _group_findings(self, findings: List[Finding]) -> List[Finding]:
        """
        Group and sort findings by severity and category.
        
        Findings are sorted by:
        1. Severity (Critical -> High -> Medium -> Low -> Info)
        2. Category (alphabetically)
        3. File path (alphabetically)
        4. Line number (numerically)
        
        Args:
            findings: List of findings to group
            
        Returns:
            Sorted list of findings
        """
        severity_order = {
            Severity.CRITICAL: 0,
            Severity.HIGH: 1,
            Severity.MEDIUM: 2,
            Severity.LOW: 3,
            Severity.INFO: 4,
        }
        
        def sort_key(finding: Finding):
            return (
                severity_order.get(finding.severity, 999),
                finding.category,
                finding.file_path,
                finding.line_number or 0,
            )
        
        return sorted(findings, key=sort_key)
    
    def _severity_meets_minimum(self, severity: Severity) -> bool:
        """Check if severity meets minimum threshold."""
        severity_order = [
            Severity.INFO,
            Severity.LOW,
            Severity.MEDIUM,
            Severity.HIGH,
            Severity.CRITICAL,
        ]
        
        min_index = severity_order.index(self.config.min_severity)
        severity_index = severity_order.index(severity)
        
        return severity_index >= min_index
    
    def scan_specific(self, categories: List[str]) -> SecurityReport:
        """
        Execute only specified analyzer categories.
        
        Args:
            categories: List of category names to run
            
        Returns:
            SecurityReport with findings from specified categories
        """
        # Temporarily filter analyzers
        original_analyzers = self.analyzers
        self.analyzers = [
            a for a in self.analyzers 
            if a.get_category() in categories
        ]
        
        try:
            report = self.scan()
        finally:
            # Restore original analyzers
            self.analyzers = original_analyzers
        
        return report
    
    def save_report(self, report: SecurityReport, output_path: Optional[str] = None) -> str:
        """
        Save report to file in configured format.
        
        Args:
            report: SecurityReport to save
            output_path: Optional custom output path (overrides config)
            
        Returns:
            Path to saved report file
        """
        # Determine output path
        if output_path is None:
            output_path = self.config.output_path
        
        if output_path is None:
            # Generate default filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = self._get_file_extension(self.config.output_format)
            output_path = f"security_report_{timestamp}.{extension}"
        
        # Generate report content based on format
        if self.config.output_format == "json":
            content = report.to_json()
        elif self.config.output_format == "html":
            content = report.to_html()
        else:  # Default to markdown
            content = report.to_markdown()
        
        # Write to file
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"Report saved to: {output_file}")
        return str(output_file)
    
    def _get_file_extension(self, format_type: str) -> str:
        """Get file extension for report format."""
        extensions = {
            "json": "json",
            "markdown": "md",
            "html": "html",
        }
        return extensions.get(format_type, "md")
