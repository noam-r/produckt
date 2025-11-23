"""Data model for security analysis reports."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict
from backend.security.models.finding import Finding, Severity


@dataclass
class SecurityReport:
    """Complete security analysis report."""
    
    scan_id: str
    scan_date: datetime
    project_path: str
    
    # Summary statistics
    total_findings: int = 0
    findings_by_severity: Dict[Severity, int] = field(default_factory=dict)
    findings_by_category: Dict[str, int] = field(default_factory=dict)
    
    # Detailed findings
    findings: List[Finding] = field(default_factory=list)
    
    # Scan metadata
    analyzers_run: List[str] = field(default_factory=list)
    files_scanned: int = 0
    scan_duration_seconds: float = 0.0
    
    def to_json(self) -> str:
        """Export report as JSON."""
        report_dict = {
            "scan_id": self.scan_id,
            "scan_date": self.scan_date.isoformat(),
            "project_path": self.project_path,
            "summary": {
                "total_findings": self.total_findings,
                "findings_by_severity": {
                    severity.value: count 
                    for severity, count in self.findings_by_severity.items()
                },
                "findings_by_category": self.findings_by_category,
            },
            "findings": [finding.to_dict() for finding in self.findings],
            "metadata": {
                "analyzers_run": self.analyzers_run,
                "files_scanned": self.files_scanned,
                "scan_duration_seconds": self.scan_duration_seconds,
            }
        }
        return json.dumps(report_dict, indent=2)
    
    def to_markdown(self) -> str:
        """Export report as Markdown."""
        lines = [
            "# Security Analysis Report",
            "",
            f"**Scan ID:** {self.scan_id}",
            f"**Scan Date:** {self.scan_date.strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Project Path:** {self.project_path}",
            "",
            "## Summary",
            "",
            f"- **Total Findings:** {self.total_findings}",
            f"- **Files Scanned:** {self.files_scanned}",
            f"- **Scan Duration:** {self.scan_duration_seconds:.2f} seconds",
            f"- **Analyzers Run:** {', '.join(self.analyzers_run)}",
            "",
            "### Findings by Severity",
            "",
        ]
        
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            count = self.findings_by_severity.get(severity, 0)
            lines.append(f"- **{severity.value.upper()}:** {count}")
        
        lines.extend([
            "",
            "### Findings by Category",
            "",
        ])
        
        for category, count in sorted(self.findings_by_category.items()):
            lines.append(f"- **{category}:** {count}")
        
        lines.extend([
            "",
            "## Detailed Findings",
            "",
        ])
        
        # Group findings by severity
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            severity_findings = [f for f in self.findings if f.severity == severity]
            if severity_findings:
                lines.extend([
                    f"### {severity.value.upper()} Severity",
                    "",
                ])
                
                for finding in severity_findings:
                    lines.extend([
                        f"#### {finding.title}",
                        "",
                        f"**Category:** {finding.category}",
                        f"**Confidence:** {finding.confidence.value}",
                        f"**File:** {finding.file_path}" + (f":{finding.line_number}" if finding.line_number else ""),
                        "",
                        f"**Description:** {finding.description}",
                        "",
                    ])
                    
                    if finding.code_snippet:
                        lines.extend([
                            "**Code Snippet:**",
                            "```python",
                            finding.code_snippet,
                            "```",
                            "",
                        ])
                    
                    if finding.remediation:
                        lines.extend([
                            f"**Remediation:** {finding.remediation}",
                            "",
                        ])
                    
                    if finding.remediation_code:
                        lines.extend([
                            "**Remediation Code:**",
                            "```python",
                            finding.remediation_code,
                            "```",
                            "",
                        ])
                    
                    if finding.references:
                        lines.extend([
                            "**References:**",
                        ])
                        for ref in finding.references:
                            lines.append(f"- {ref}")
                        lines.append("")
                    
                    lines.append("---")
                    lines.append("")
        
        return "\n".join(lines)
    
    def to_html(self) -> str:
        """Export report as HTML."""
        severity_colors = {
            Severity.CRITICAL: "#dc3545",
            Severity.HIGH: "#fd7e14",
            Severity.MEDIUM: "#ffc107",
            Severity.LOW: "#17a2b8",
            Severity.INFO: "#6c757d",
        }
        
        html_parts = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<meta charset='UTF-8'>",
            "<title>Security Analysis Report</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }",
            ".container { max-width: 1200px; margin: 0 auto; background-color: white; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }",
            "h1 { color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }",
            "h2 { color: #555; margin-top: 30px; }",
            "h3 { color: #666; margin-top: 20px; }",
            ".summary { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }",
            ".finding { border: 1px solid #ddd; padding: 15px; margin: 15px 0; border-radius: 5px; }",
            ".severity-badge { display: inline-block; padding: 5px 10px; border-radius: 3px; color: white; font-weight: bold; }",
            ".code-snippet { background-color: #f4f4f4; padding: 10px; border-left: 3px solid #007bff; overflow-x: auto; }",
            "pre { margin: 0; }",
            ".metadata { color: #666; font-size: 0.9em; }",
            "</style>",
            "</head>",
            "<body>",
            "<div class='container'>",
            "<h1>Security Analysis Report</h1>",
            f"<div class='metadata'>",
            f"<p><strong>Scan ID:</strong> {self.scan_id}</p>",
            f"<p><strong>Scan Date:</strong> {self.scan_date.strftime('%Y-%m-%d %H:%M:%S')}</p>",
            f"<p><strong>Project Path:</strong> {self.project_path}</p>",
            f"</div>",
            "<div class='summary'>",
            "<h2>Summary</h2>",
            f"<p><strong>Total Findings:</strong> {self.total_findings}</p>",
            f"<p><strong>Files Scanned:</strong> {self.files_scanned}</p>",
            f"<p><strong>Scan Duration:</strong> {self.scan_duration_seconds:.2f} seconds</p>",
            f"<p><strong>Analyzers Run:</strong> {', '.join(self.analyzers_run)}</p>",
            "<h3>Findings by Severity</h3>",
            "<ul>",
        ]
        
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            count = self.findings_by_severity.get(severity, 0)
            html_parts.append(f"<li><strong>{severity.value.upper()}:</strong> {count}</li>")
        
        html_parts.extend([
            "</ul>",
            "<h3>Findings by Category</h3>",
            "<ul>",
        ])
        
        for category, count in sorted(self.findings_by_category.items()):
            html_parts.append(f"<li><strong>{category}:</strong> {count}</li>")
        
        html_parts.extend([
            "</ul>",
            "</div>",
            "<h2>Detailed Findings</h2>",
        ])
        
        # Group findings by severity
        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            severity_findings = [f for f in self.findings if f.severity == severity]
            if severity_findings:
                html_parts.append(f"<h3>{severity.value.upper()} Severity</h3>")
                
                for finding in severity_findings:
                    color = severity_colors.get(severity, "#6c757d")
                    html_parts.extend([
                        "<div class='finding'>",
                        f"<h4>{finding.title} <span class='severity-badge' style='background-color: {color};'>{finding.severity.value.upper()}</span></h4>",
                        f"<p><strong>Category:</strong> {finding.category}</p>",
                        f"<p><strong>Confidence:</strong> {finding.confidence.value}</p>",
                        f"<p><strong>File:</strong> {finding.file_path}" + (f":{finding.line_number}" if finding.line_number else "") + "</p>",
                        f"<p><strong>Description:</strong> {finding.description}</p>",
                    ])
                    
                    if finding.code_snippet:
                        html_parts.extend([
                            "<p><strong>Code Snippet:</strong></p>",
                            "<div class='code-snippet'>",
                            f"<pre>{finding.code_snippet}</pre>",
                            "</div>",
                        ])
                    
                    if finding.remediation:
                        html_parts.append(f"<p><strong>Remediation:</strong> {finding.remediation}</p>")
                    
                    if finding.remediation_code:
                        html_parts.extend([
                            "<p><strong>Remediation Code:</strong></p>",
                            "<div class='code-snippet'>",
                            f"<pre>{finding.remediation_code}</pre>",
                            "</div>",
                        ])
                    
                    if finding.references:
                        html_parts.append("<p><strong>References:</strong></p><ul>")
                        for ref in finding.references:
                            html_parts.append(f"<li><a href='{ref}' target='_blank'>{ref}</a></li>")
                        html_parts.append("</ul>")
                    
                    html_parts.append("</div>")
        
        html_parts.extend([
            "</div>",
            "</body>",
            "</html>",
        ])
        
        return "\n".join(html_parts)
