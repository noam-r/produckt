"""Severity calculation logic based on OWASP risk methodology."""

from enum import Enum
from typing import Optional, Dict
from dataclasses import dataclass


class Severity(str, Enum):
    """Severity levels for security findings."""
    
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Confidence(str, Enum):
    """Confidence levels for security findings."""
    
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class RiskFactors:
    """Risk factors for OWASP risk calculation."""
    
    # Likelihood factors (0-9 scale)
    threat_agent_skill: int = 5  # How skilled is the attacker?
    motive: int = 5  # How motivated is the attacker?
    opportunity: int = 5  # How easy is it to discover?
    size: int = 5  # How large is the attack surface?
    
    # Impact factors (0-9 scale)
    confidentiality: int = 5  # Data exposure impact
    integrity: int = 5  # Data modification impact
    availability: int = 5  # Service disruption impact
    accountability: int = 5  # Traceability impact


class SeverityCalculator:
    """Calculate severity based on OWASP risk methodology."""
    
    # Severity thresholds based on overall risk score
    SEVERITY_THRESHOLDS = {
        Severity.CRITICAL: 9.0,
        Severity.HIGH: 7.0,
        Severity.MEDIUM: 4.0,
        Severity.LOW: 1.0,
        Severity.INFO: 0.0,
    }
    
    # Predefined risk profiles for common vulnerability types
    VULNERABILITY_PROFILES: Dict[str, RiskFactors] = {
        # Authentication vulnerabilities
        "weak_password_hashing": RiskFactors(
            threat_agent_skill=3, motive=9, opportunity=7, size=9,
            confidentiality=9, integrity=9, availability=5, accountability=9
        ),
        "missing_brute_force_protection": RiskFactors(
            threat_agent_skill=1, motive=9, opportunity=9, size=9,
            confidentiality=9, integrity=7, availability=5, accountability=7
        ),
        "insecure_session_storage": RiskFactors(
            threat_agent_skill=5, motive=8, opportunity=6, size=7,
            confidentiality=8, integrity=7, availability=6, accountability=8
        ),
        "insecure_cookie_config": RiskFactors(
            threat_agent_skill=3, motive=7, opportunity=8, size=8,
            confidentiality=7, integrity=6, availability=3, accountability=6
        ),
        
        # Authorization vulnerabilities
        "missing_authorization": RiskFactors(
            threat_agent_skill=1, motive=9, opportunity=9, size=9,
            confidentiality=9, integrity=9, availability=7, accountability=9
        ),
        "privilege_escalation": RiskFactors(
            threat_agent_skill=5, motive=9, opportunity=7, size=6,
            confidentiality=9, integrity=9, availability=8, accountability=9
        ),
        "missing_tenant_isolation": RiskFactors(
            threat_agent_skill=3, motive=8, opportunity=8, size=7,
            confidentiality=9, integrity=9, availability=5, accountability=8
        ),
        
        # Data protection vulnerabilities
        "sql_injection": RiskFactors(
            threat_agent_skill=5, motive=9, opportunity=7, size=6,
            confidentiality=9, integrity=9, availability=7, accountability=9
        ),
        "sensitive_data_exposure": RiskFactors(
            threat_agent_skill=1, motive=8, opportunity=9, size=8,
            confidentiality=9, integrity=5, availability=3, accountability=7
        ),
        "missing_input_validation": RiskFactors(
            threat_agent_skill=3, motive=7, opportunity=8, size=7,
            confidentiality=7, integrity=8, availability=6, accountability=6
        ),
        
        # API security vulnerabilities
        "cors_misconfiguration": RiskFactors(
            threat_agent_skill=3, motive=6, opportunity=8, size=8,
            confidentiality=6, integrity=7, availability=4, accountability=5
        ),
        "missing_rate_limiting": RiskFactors(
            threat_agent_skill=1, motive=5, opportunity=9, size=9,
            confidentiality=3, integrity=4, availability=8, accountability=4
        ),
        "xss_vulnerability": RiskFactors(
            threat_agent_skill=3, motive=7, opportunity=7, size=7,
            confidentiality=6, integrity=8, availability=4, accountability=6
        ),
        "csrf_vulnerability": RiskFactors(
            threat_agent_skill=3, motive=7, opportunity=6, size=6,
            confidentiality=5, integrity=9, availability=5, accountability=7
        ),
        
        # Infrastructure vulnerabilities
        "hardcoded_secrets": RiskFactors(
            threat_agent_skill=1, motive=9, opportunity=8, size=7,
            confidentiality=9, integrity=8, availability=6, accountability=8
        ),
        "debug_mode_enabled": RiskFactors(
            threat_agent_skill=2, motive=6, opportunity=9, size=8,
            confidentiality=7, integrity=5, availability=5, accountability=6
        ),
        "sensitive_data_in_logs": RiskFactors(
            threat_agent_skill=2, motive=7, opportunity=7, size=7,
            confidentiality=8, integrity=3, availability=3, accountability=6
        ),
        "outdated_dependencies": RiskFactors(
            threat_agent_skill=4, motive=7, opportunity=6, size=6,
            confidentiality=7, integrity=7, availability=7, accountability=6
        ),
    }
    
    def __init__(self, overrides: Optional[Dict[str, Severity]] = None):
        """
        Initialize severity calculator.
        
        Args:
            overrides: Optional dictionary of vulnerability_type -> Severity overrides
        """
        self.overrides = overrides or {}
    
    def calculate_severity(
        self,
        vulnerability_type: str,
        risk_factors: Optional[RiskFactors] = None
    ) -> Severity:
        """
        Calculate severity for a vulnerability.
        
        Args:
            vulnerability_type: Type of vulnerability
            risk_factors: Optional custom risk factors
            
        Returns:
            Severity level
        """
        # Check for override
        if vulnerability_type in self.overrides:
            return self.overrides[vulnerability_type]
        
        # Use provided risk factors or lookup predefined profile
        if risk_factors is None:
            risk_factors = self.VULNERABILITY_PROFILES.get(
                vulnerability_type,
                RiskFactors()  # Default medium risk
            )
        
        # Calculate OWASP risk score
        risk_score = self._calculate_owasp_risk(risk_factors)
        
        # Map risk score to severity
        return self._risk_score_to_severity(risk_score)
    
    def calculate_confidence(
        self,
        has_context: bool = True,
        is_pattern_specific: bool = True,
        has_false_positive_risk: bool = False
    ) -> Confidence:
        """
        Calculate confidence level for a finding.
        
        Args:
            has_context: Whether we have full code context
            is_pattern_specific: Whether pattern is specific (not generic)
            has_false_positive_risk: Whether there's risk of false positive
            
        Returns:
            Confidence level
        """
        confidence_score = 0
        
        if has_context:
            confidence_score += 1
        
        if is_pattern_specific:
            confidence_score += 1
        
        if not has_false_positive_risk:
            confidence_score += 1
        
        if confidence_score >= 3:
            return Confidence.HIGH
        elif confidence_score >= 2:
            return Confidence.MEDIUM
        else:
            return Confidence.LOW
    
    def _calculate_owasp_risk(self, factors: RiskFactors) -> float:
        """
        Calculate OWASP risk score from risk factors.
        
        OWASP Risk = (Likelihood + Impact) / 2
        Where Likelihood and Impact are averages of their respective factors.
        
        Args:
            factors: Risk factors
            
        Returns:
            Risk score (0-9)
        """
        # Calculate likelihood (average of threat agent factors)
        likelihood = (
            factors.threat_agent_skill +
            factors.motive +
            factors.opportunity +
            factors.size
        ) / 4.0
        
        # Calculate impact (average of technical/business impact factors)
        impact = (
            factors.confidentiality +
            factors.integrity +
            factors.availability +
            factors.accountability
        ) / 4.0
        
        # Overall risk is average of likelihood and impact
        risk_score = (likelihood + impact) / 2.0
        
        return risk_score
    
    def _risk_score_to_severity(self, risk_score: float) -> Severity:
        """
        Map OWASP risk score to severity level.
        
        Args:
            risk_score: Risk score (0-9)
            
        Returns:
            Severity level
        """
        for severity, threshold in self.SEVERITY_THRESHOLDS.items():
            if risk_score >= threshold:
                return severity
        
        return Severity.INFO
    
    def add_override(self, vulnerability_type: str, severity: Severity):
        """
        Add a severity override for a vulnerability type.
        
        Args:
            vulnerability_type: Type of vulnerability
            severity: Severity to override with
        """
        self.overrides[vulnerability_type] = severity
    
    def remove_override(self, vulnerability_type: str):
        """
        Remove a severity override.
        
        Args:
            vulnerability_type: Type of vulnerability
        """
        self.overrides.pop(vulnerability_type, None)
    
    @staticmethod
    def get_severity_order(severity: Severity) -> int:
        """
        Get numeric order for severity (higher = more severe).
        
        Args:
            severity: Severity level
            
        Returns:
            Numeric order (0-4)
        """
        order = {
            Severity.CRITICAL: 4,
            Severity.HIGH: 3,
            Severity.MEDIUM: 2,
            Severity.LOW: 1,
            Severity.INFO: 0,
        }
        return order.get(severity, 0)
    
    @staticmethod
    def compare_severity(sev1: Severity, sev2: Severity) -> int:
        """
        Compare two severity levels.
        
        Args:
            sev1: First severity
            sev2: Second severity
            
        Returns:
            -1 if sev1 < sev2, 0 if equal, 1 if sev1 > sev2
        """
        order1 = SeverityCalculator.get_severity_order(sev1)
        order2 = SeverityCalculator.get_severity_order(sev2)
        
        if order1 < order2:
            return -1
        elif order1 > order2:
            return 1
        else:
            return 0
