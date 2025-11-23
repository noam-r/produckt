"""Data model for security vulnerability findings."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List


class Severity(str, Enum):
    """Severity levels for security findings based on OWASP risk methodology."""
    CRITICAL = "critical"  # Immediate action required
    HIGH = "high"          # Should be fixed soon
    MEDIUM = "medium"      # Should be addressed
    LOW = "low"            # Minor issue
    INFO = "info"          # Informational only


class Confidence(str, Enum):
    """Confidence level in the finding accuracy."""
    HIGH = "high"      # Very likely a real vulnerability
    MEDIUM = "medium"  # Probably a vulnerability, may need verification
    LOW = "low"        # Possible vulnerability, likely needs manual review


@dataclass
class Finding:
    """Represents a single security vulnerability finding."""
    
    id: str                          # Unique finding identifier
    category: str                    # authentication, authorization, etc.
    title: str                       # Short description
    description: str                 # Detailed explanation
    severity: Severity               # CRITICAL, HIGH, MEDIUM, LOW, INFO
    confidence: Confidence           # HIGH, MEDIUM, LOW
    
    # Location information
    file_path: str                   # Relative path to affected file
    line_number: Optional[int] = None       # Line number if applicable
    code_snippet: Optional[str] = None      # Relevant code excerpt
    
    # Remediation
    remediation: str = ""                   # How to fix the issue
    remediation_code: Optional[str] = None  # Example fix code
    
    # References
    cwe_id: Optional[str] = None            # CWE identifier
    owasp_category: Optional[str] = None    # OWASP Top 10 category
    references: List[str] = field(default_factory=list)  # External reference URLs
    
    # Metadata
    detected_by: str = ""                   # Analyzer that found this
    detected_at: datetime = field(default_factory=datetime.now)  # When it was found
    
    def to_dict(self) -> dict:
        """Convert finding to dictionary representation."""
        return {
            "id": self.id,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "severity": self.severity.value,
            "confidence": self.confidence.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "code_snippet": self.code_snippet,
            "remediation": self.remediation,
            "remediation_code": self.remediation_code,
            "cwe_id": self.cwe_id,
            "owasp_category": self.owasp_category,
            "references": self.references,
            "detected_by": self.detected_by,
            "detected_at": self.detected_at.isoformat(),
        }
