"""Authentication security analyzer for detecting authentication vulnerabilities."""

import re
import uuid
from typing import List, Optional
from backend.security.analyzers.base import BaseAnalyzer
from backend.security.models.finding import Finding, Severity, Confidence
from backend.security.utils.pattern_matcher import PatternMatcher
from backend.security.utils.ast_parser import ASTParser
from backend.security.utils.severity import SeverityCalculator


class AuthenticationAnalyzer(BaseAnalyzer):
    """
    Analyzer for authentication-related security vulnerabilities.
    
    Detects issues including:
    - Weak password hashing algorithms
    - Insufficient bcrypt rounds
    - Insecure session storage
    - Missing session expiration
    - Weak password policies
    - Missing brute force protection
    - Insecure cookie configurations
    """
    
    def __init__(self):
        """Initialize authentication analyzer."""
        super().__init__()
        self.pattern_matcher = PatternMatcher(context_lines=3)
        self.ast_parser = ASTParser()
        self.severity_calculator = SeverityCalculator()
    
    def get_category(self) -> str:
        """Return the security category."""
        return "authentication"
    
    def analyze(self, file_path: str, content: str) -> List[Finding]:
        """
        Analyze a file for authentication vulnerabilities.
        
        Args:
            file_path: Relative path to the file
            content: File content
            
        Returns:
            List of security findings
        """
        findings = []
        
        # Parse AST for structural analysis
        ast_parsed = self.ast_parser.parse(content)
        
        # Check password hashing strength
        findings.extend(self._check_password_hashing(file_path, content))
        
        # Check session storage security
        findings.extend(self._check_session_storage(file_path, content))
        
        # Check password policy validation
        findings.extend(self._check_password_policy(file_path, content))
        
        # Check brute force protection on login endpoints
        if ast_parsed:
            findings.extend(self._check_brute_force_protection(file_path, content))
        
        # Check cookie security
        findings.extend(self._check_cookie_security(file_path, content))
        
        return findings
    
    def _check_password_hashing(self, file_path: str, content: str) -> List[Finding]:
        """Check for weak password hashing algorithms and configurations."""
        findings = []
        
        # Check for weak hashing algorithms (MD5, SHA1, SHA256 for passwords)
        weak_hash_patterns = [
            (r'hashlib\.(md5|sha1|sha256)\s*\(.*password', 'weak_hash_algorithm'),
            (r'(md5|sha1|sha256)\s*\(.*password', 'weak_hash_algorithm'),
            (r'password.*=.*hashlib\.(md5|sha1|sha256)', 'weak_hash_algorithm'),
        ]
        
        for pattern, pattern_name in weak_hash_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                finding_id = f"auth-weak-hash-{file_path}-{match.line_number}"
                severity = self.severity_calculator.calculate_severity("weak_password_hashing")
                confidence = self.severity_calculator.calculate_confidence(
                    has_context=True,
                    is_pattern_specific=True,
                    has_false_positive_risk=False
                )
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Weak Password Hashing Algorithm",
                    description=(
                        f"Detected use of weak hashing algorithm for password storage. "
                        f"Algorithms like MD5, SHA1, and SHA256 are not suitable for password "
                        f"hashing as they are too fast and vulnerable to brute force attacks. "
                        f"Found: {match.matched_text}"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Use bcrypt, scrypt, or Argon2 for password hashing. These algorithms "
                        "are specifically designed for password storage with built-in salting "
                        "and configurable work factors."
                    ),
                    remediation_code=(
                        "import bcrypt\n\n"
                        "def hash_password(password: str) -> str:\n"
                        "    password_bytes = password.encode('utf-8')\n"
                        "    salt = bcrypt.gensalt(rounds=12)  # 12+ rounds recommended\n"
                        "    hashed = bcrypt.hashpw(password_bytes, salt)\n"
                        "    return hashed.decode('utf-8')"
                    ),
                    cwe_id="CWE-916",
                    owasp_category="A02:2021 - Cryptographic Failures",
                    references=[
                        "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/04-Testing_for_Weak_Encryption",
                        "https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Check for insufficient bcrypt rounds
        bcrypt_rounds_pattern = r'bcrypt\.gensalt\s*\(\s*(?:rounds\s*=\s*)?(\d+)\s*\)'
        matches = self.pattern_matcher.match_pattern(
            bcrypt_rounds_pattern, content, 'bcrypt_rounds'
        )
        
        for match in matches:
            # Extract the rounds value
            rounds_match = re.search(r'(\d+)', match.matched_text)
            if rounds_match:
                rounds = int(rounds_match.group(1))
                if rounds < 12:
                    finding_id = f"auth-weak-bcrypt-{file_path}-{match.line_number}"
                    severity = self.severity_calculator.calculate_severity("weak_password_hashing")
                    confidence = Confidence.HIGH
                    
                    findings.append(Finding(
                        id=finding_id,
                        category=self.get_category(),
                        title="Insufficient Bcrypt Rounds",
                        description=(
                            f"Bcrypt is configured with {rounds} rounds, which is below the "
                            f"recommended minimum of 12. Lower rounds make passwords more "
                            f"vulnerable to brute force attacks."
                        ),
                        severity=severity,
                        confidence=confidence,
                        file_path=file_path,
                        line_number=match.line_number,
                        code_snippet=match.code_snippet,
                        remediation=(
                            "Increase bcrypt rounds to at least 12. The recommended value is "
                            "12-14 rounds, balancing security and performance."
                        ),
                        remediation_code="salt = bcrypt.gensalt(rounds=12)  # Minimum 12 rounds",
                        cwe_id="CWE-916",
                        owasp_category="A02:2021 - Cryptographic Failures",
                        references=[
                            "https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html"
                        ],
                        detected_by=self.get_name()
                    ))
        
        # Check for missing salt in password hashing
        no_salt_patterns = [
            (r'hashlib\.\w+\(password\)', 'no_salt'),
            (r'hash\(password\)', 'no_salt'),
        ]
        
        for pattern, pattern_name in no_salt_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                # Skip if bcrypt is used (has built-in salting)
                if 'bcrypt' in match.code_snippet.lower():
                    continue
                
                finding_id = f"auth-no-salt-{file_path}-{match.line_number}"
                severity = self.severity_calculator.calculate_severity("weak_password_hashing")
                confidence = Confidence.MEDIUM
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Password Hashing Without Salt",
                    description=(
                        "Password hashing appears to be performed without a salt. "
                        "Unsalted password hashes are vulnerable to rainbow table attacks."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Always use a unique salt for each password. Use bcrypt which "
                        "handles salting automatically, or generate a cryptographically "
                        "secure random salt for each password."
                    ),
                    cwe_id="CWE-759",
                    owasp_category="A02:2021 - Cryptographic Failures",
                    references=[
                        "https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        return findings

    def _check_session_storage(self, file_path: str, content: str) -> List[Finding]:
        """Check for insecure session storage mechanisms."""
        findings = []
        
        # Check for in-memory session storage without persistence
        in_memory_patterns = [
            (r'self\._sessions\s*:\s*Dict\[.*\]\s*=\s*\{\}', 'in_memory_dict'),
            (r'sessions\s*=\s*\{\}', 'in_memory_dict'),
            (r'_sessions\s*=\s*dict\(\)', 'in_memory_dict'),
        ]
        
        for pattern, pattern_name in in_memory_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name
            )
            
            for match in matches:
                # Check if this is in a SessionManager or similar class
                if 'session' in content.lower() and 'class' in content[:match.line_number * 100]:
                    finding_id = f"auth-inmem-session-{file_path}-{match.line_number}"
                    severity = self.severity_calculator.calculate_severity("insecure_session_storage")
                    confidence = Confidence.HIGH
                    
                    findings.append(Finding(
                        id=finding_id,
                        category=self.get_category(),
                        title="In-Memory Session Storage",
                        description=(
                            "Sessions are stored in memory using a dictionary. This approach "
                            "has several security and scalability issues:\n"
                            "1. Sessions are lost on server restart\n"
                            "2. Does not scale across multiple server instances\n"
                            "3. Memory usage grows unbounded with active sessions\n"
                            "4. No persistence for session audit trails"
                        ),
                        severity=severity,
                        confidence=confidence,
                        file_path=file_path,
                        line_number=match.line_number,
                        code_snippet=match.code_snippet,
                        remediation=(
                            "Use a persistent session store like Redis or a database. "
                            "Redis is recommended for session storage as it provides:\n"
                            "- Automatic expiration with TTL\n"
                            "- Persistence across restarts\n"
                            "- Horizontal scalability\n"
                            "- Built-in atomic operations"
                        ),
                        remediation_code=(
                            "import redis\n\n"
                            "class SessionManager:\n"
                            "    def __init__(self):\n"
                            "        self.redis_client = redis.Redis(\n"
                            "            host='localhost',\n"
                            "            port=6379,\n"
                            "            decode_responses=True\n"
                            "        )\n"
                            "    \n"
                            "    def create_session(self, user_id, data):\n"
                            "        session_id = secrets.token_urlsafe(32)\n"
                            "        self.redis_client.setex(\n"
                            "            f'session:{session_id}',\n"
                            "            timedelta(hours=24),\n"
                            "            json.dumps(data)\n"
                            "        )\n"
                            "        return session_id"
                        ),
                        cwe_id="CWE-613",
                        owasp_category="A07:2021 - Identification and Authentication Failures",
                        references=[
                            "https://owasp.org/www-community/vulnerabilities/Insufficient_Session-ID_Length",
                            "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html"
                        ],
                        detected_by=self.get_name()
                    ))
        
        # Check for missing session expiration
        if 'session' in content.lower() and 'class' in content:
            # Look for session creation without expiration
            has_expiration = bool(re.search(
                r'(expires_at|expiration|ttl|max_age|timedelta)',
                content,
                re.IGNORECASE
            ))
            
            has_session_creation = bool(re.search(
                r'(create_session|new_session|session_id\s*=)',
                content,
                re.IGNORECASE
            ))
            
            if has_session_creation and not has_expiration:
                finding_id = f"auth-no-expiration-{file_path}"
                severity = self.severity_calculator.calculate_severity("insecure_session_storage")
                confidence = Confidence.MEDIUM
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Missing Session Expiration",
                    description=(
                        "Session creation detected without explicit expiration time. "
                        "Sessions without expiration can remain valid indefinitely, "
                        "increasing the risk of session hijacking and unauthorized access."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=None,
                    code_snippet=None,
                    remediation=(
                        "Always set an expiration time for sessions. Recommended values:\n"
                        "- Web applications: 15-30 minutes of inactivity\n"
                        "- API tokens: 1-24 hours\n"
                        "- Remember me tokens: 30 days maximum\n"
                        "Implement both absolute and idle timeouts."
                    ),
                    remediation_code=(
                        "from datetime import datetime, timedelta\n\n"
                        "session.expires_at = datetime.utcnow() + timedelta(minutes=30)\n"
                        "session.last_activity = datetime.utcnow()  # For idle timeout"
                    ),
                    cwe_id="CWE-613",
                    owasp_category="A07:2021 - Identification and Authentication Failures",
                    references=[
                        "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        return findings
    
    def _check_password_policy(self, file_path: str, content: str) -> List[Finding]:
        """Check for weak or missing password policy validation."""
        findings = []
        
        # Check if this file handles password validation
        has_password_validation = bool(re.search(
            r'(validate.*password|password.*valid|check.*password)',
            content,
            re.IGNORECASE
        ))
        
        if not has_password_validation:
            return findings
        
        # Check for minimum length requirement
        has_length_check = bool(re.search(
            r'len\(password\)\s*[<>=]+\s*\d+',
            content
        ))
        
        if not has_length_check:
            finding_id = f"auth-no-length-check-{file_path}"
            severity = Severity.MEDIUM
            confidence = Confidence.MEDIUM
            
            findings.append(Finding(
                id=finding_id,
                category=self.get_category(),
                title="Missing Password Length Validation",
                description=(
                    "Password validation function detected without minimum length check. "
                    "Short passwords are easier to crack through brute force attacks."
                ),
                severity=severity,
                confidence=confidence,
                file_path=file_path,
                line_number=None,
                code_snippet=None,
                remediation=(
                    "Enforce a minimum password length of at least 8 characters, "
                    "preferably 12 or more. NIST recommends allowing passwords up to "
                    "64 characters or more."
                ),
                remediation_code=(
                    "if len(password) < 12:\n"
                    "    raise ValueError('Password must be at least 12 characters long')"
                ),
                cwe_id="CWE-521",
                owasp_category="A07:2021 - Identification and Authentication Failures",
                references=[
                    "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html"
                ],
                detected_by=self.get_name()
            ))
        
        # Check for complexity requirements (uppercase, lowercase, digits, special chars)
        has_complexity_check = bool(re.search(
            r'(isupper|islower|isdigit|[A-Z].*[a-z]|[a-z].*[A-Z])',
            content
        ))
        
        if not has_complexity_check:
            finding_id = f"auth-no-complexity-{file_path}"
            severity = Severity.LOW
            confidence = Confidence.MEDIUM
            
            findings.append(Finding(
                id=finding_id,
                category=self.get_category(),
                title="Missing Password Complexity Requirements",
                description=(
                    "Password validation does not check for character diversity. "
                    "While length is more important than complexity, requiring a mix "
                    "of character types can improve password strength."
                ),
                severity=severity,
                confidence=confidence,
                file_path=file_path,
                line_number=None,
                code_snippet=None,
                remediation=(
                    "Consider requiring passwords to contain:\n"
                    "- At least one uppercase letter\n"
                    "- At least one lowercase letter\n"
                    "- At least one digit\n"
                    "- At least one special character\n"
                    "However, prioritize length over complexity."
                ),
                remediation_code=(
                    "import re\n\n"
                    "if not re.search(r'[A-Z]', password):\n"
                    "    raise ValueError('Password must contain uppercase letter')\n"
                    "if not re.search(r'[a-z]', password):\n"
                    "    raise ValueError('Password must contain lowercase letter')\n"
                    "if not re.search(r'[0-9]', password):\n"
                    "    raise ValueError('Password must contain digit')"
                ),
                cwe_id="CWE-521",
                owasp_category="A07:2021 - Identification and Authentication Failures",
                references=[
                    "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html"
                ],
                detected_by=self.get_name()
            ))
        
        # Check for common password detection
        has_common_password_check = bool(re.search(
            r'(common.*password|password.*list|blacklist)',
            content,
            re.IGNORECASE
        ))
        
        if not has_common_password_check:
            finding_id = f"auth-no-common-check-{file_path}"
            severity = Severity.LOW
            confidence = Confidence.LOW
            
            findings.append(Finding(
                id=finding_id,
                category=self.get_category(),
                title="Missing Common Password Check",
                description=(
                    "Password validation does not check against common passwords. "
                    "Users often choose weak, commonly-used passwords that are "
                    "easily guessed or found in password dictionaries."
                ),
                severity=severity,
                confidence=confidence,
                file_path=file_path,
                line_number=None,
                code_snippet=None,
                remediation=(
                    "Check passwords against a list of common passwords. "
                    "Consider using the 'Have I Been Pwned' API or maintaining "
                    "a local list of the top 10,000 most common passwords."
                ),
                remediation_code=(
                    "COMMON_PASSWORDS = {'password', '123456', 'qwerty', ...}\n\n"
                    "if password.lower() in COMMON_PASSWORDS:\n"
                    "    raise ValueError('Password is too common')"
                ),
                cwe_id="CWE-521",
                owasp_category="A07:2021 - Identification and Authentication Failures",
                references=[
                    "https://haveibeenpwned.com/Passwords",
                    "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html"
                ],
                detected_by=self.get_name()
            ))
        
        return findings

    def _check_brute_force_protection(self, file_path: str, content: str) -> List[Finding]:
        """Check for missing brute force protection on authentication endpoints."""
        findings = []
        
        # Look for login/authentication endpoints
        login_patterns = [
            r'@router\.(post|put)\s*\(\s*["\'].*/(login|auth|signin)',
            r'def\s+(login|authenticate|signin)\s*\(',
        ]
        
        has_login_endpoint = False
        login_line = None
        
        for pattern in login_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, 'login_endpoint', flags=re.IGNORECASE
            )
            if matches:
                has_login_endpoint = True
                login_line = matches[0].line_number
                break
        
        if not has_login_endpoint:
            return findings
        
        # Check for rate limiting
        has_rate_limiting = bool(re.search(
            r'(rate.*limit|RateLimit|Limiter|throttle)',
            content,
            re.IGNORECASE
        ))
        
        # Check for account lockout
        has_lockout = bool(re.search(
            r'(lockout|lock.*account|failed.*attempt|login.*attempt)',
            content,
            re.IGNORECASE
        ))
        
        # Check for CAPTCHA
        has_captcha = bool(re.search(
            r'(captcha|recaptcha)',
            content,
            re.IGNORECASE
        ))
        
        if not (has_rate_limiting or has_lockout or has_captcha):
            finding_id = f"auth-no-brute-force-{file_path}-{login_line}"
            severity = self.severity_calculator.calculate_severity("missing_brute_force_protection")
            confidence = Confidence.HIGH
            
            findings.append(Finding(
                id=finding_id,
                category=self.get_category(),
                title="Missing Brute Force Protection on Login Endpoint",
                description=(
                    "Login endpoint detected without brute force protection mechanisms. "
                    "Attackers can attempt unlimited login attempts to guess passwords. "
                    "No rate limiting, account lockout, or CAPTCHA detected."
                ),
                severity=severity,
                confidence=confidence,
                file_path=file_path,
                line_number=login_line,
                code_snippet=None,
                remediation=(
                    "Implement brute force protection using one or more of:\n"
                    "1. Rate limiting: Limit login attempts per IP/user (e.g., 5 per minute)\n"
                    "2. Account lockout: Lock account after N failed attempts (e.g., 5-10)\n"
                    "3. Progressive delays: Increase delay after each failed attempt\n"
                    "4. CAPTCHA: Require CAPTCHA after several failed attempts\n"
                    "5. Multi-factor authentication: Add second factor for authentication"
                ),
                remediation_code=(
                    "from slowapi import Limiter\n"
                    "from slowapi.util import get_remote_address\n\n"
                    "limiter = Limiter(key_func=get_remote_address)\n\n"
                    "@router.post('/login')\n"
                    "@limiter.limit('5/minute')  # 5 attempts per minute\n"
                    "async def login(request: Request, ...):\n"
                    "    # Also track failed attempts per user\n"
                    "    if user.failed_login_attempts >= 5:\n"
                    "        raise HTTPException(423, 'Account locked')\n"
                    "    ..."
                ),
                cwe_id="CWE-307",
                owasp_category="A07:2021 - Identification and Authentication Failures",
                references=[
                    "https://owasp.org/www-community/controls/Blocking_Brute_Force_Attacks",
                    "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html"
                ],
                detected_by=self.get_name()
            ))
        
        # Check specifically for rate limiting on auth routes
        if has_login_endpoint and not has_rate_limiting:
            finding_id = f"auth-no-rate-limit-{file_path}-{login_line}"
            severity = Severity.HIGH
            confidence = Confidence.HIGH
            
            findings.append(Finding(
                id=finding_id,
                category=self.get_category(),
                title="Missing Rate Limiting on Authentication Route",
                description=(
                    "Authentication endpoint does not implement rate limiting. "
                    "This allows attackers to make unlimited authentication attempts, "
                    "facilitating credential stuffing and brute force attacks."
                ),
                severity=severity,
                confidence=confidence,
                file_path=file_path,
                line_number=login_line,
                code_snippet=None,
                remediation=(
                    "Apply rate limiting to authentication endpoints. Recommended limits:\n"
                    "- 5-10 attempts per minute per IP address\n"
                    "- 3-5 attempts per minute per username\n"
                    "- Use sliding window or token bucket algorithms"
                ),
                remediation_code=(
                    "from fastapi import Request\n"
                    "from slowapi import Limiter\n\n"
                    "limiter = Limiter(key_func=get_remote_address)\n\n"
                    "@router.post('/login')\n"
                    "@limiter.limit('5/minute')\n"
                    "async def login(request: Request, ...):\n"
                    "    ..."
                ),
                cwe_id="CWE-307",
                owasp_category="A07:2021 - Identification and Authentication Failures",
                references=[
                    "https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html"
                ],
                detected_by=self.get_name()
            ))
        
        # Check for account lockout mechanism
        if has_login_endpoint and not has_lockout:
            finding_id = f"auth-no-lockout-{file_path}-{login_line}"
            severity = Severity.MEDIUM
            confidence = Confidence.MEDIUM
            
            findings.append(Finding(
                id=finding_id,
                category=self.get_category(),
                title="Missing Account Lockout Mechanism",
                description=(
                    "Authentication endpoint does not implement account lockout after "
                    "repeated failed login attempts. This allows unlimited password "
                    "guessing attempts against user accounts."
                ),
                severity=severity,
                confidence=confidence,
                file_path=file_path,
                line_number=login_line,
                code_snippet=None,
                remediation=(
                    "Implement account lockout after a threshold of failed attempts:\n"
                    "1. Track failed login attempts per user\n"
                    "2. Lock account after 5-10 failed attempts\n"
                    "3. Implement time-based unlock (e.g., 15-30 minutes)\n"
                    "4. Provide account recovery mechanism\n"
                    "5. Log lockout events for security monitoring"
                ),
                remediation_code=(
                    "# In User model\n"
                    "failed_login_attempts: int = 0\n"
                    "locked_until: Optional[datetime] = None\n\n"
                    "# In login endpoint\n"
                    "if user.locked_until and user.locked_until > datetime.utcnow():\n"
                    "    raise HTTPException(423, 'Account locked')\n\n"
                    "if not verify_password(password, user.password_hash):\n"
                    "    user.failed_login_attempts += 1\n"
                    "    if user.failed_login_attempts >= 5:\n"
                    "        user.locked_until = datetime.utcnow() + timedelta(minutes=30)\n"
                    "    db.commit()\n"
                    "    raise HTTPException(401, 'Invalid credentials')\n\n"
                    "# Reset on successful login\n"
                    "user.failed_login_attempts = 0\n"
                    "user.locked_until = None"
                ),
                cwe_id="CWE-307",
                owasp_category="A07:2021 - Identification and Authentication Failures",
                references=[
                    "https://owasp.org/www-community/controls/Blocking_Brute_Force_Attacks"
                ],
                detected_by=self.get_name()
            ))
        
        return findings
    
    def _check_cookie_security(self, file_path: str, content: str) -> List[Finding]:
        """Check for insecure cookie configurations."""
        findings = []
        
        # Look for set_cookie calls
        cookie_pattern = r'(set_cookie|SetCookie)\s*\('
        matches = self.pattern_matcher.match_pattern(
            cookie_pattern, content, 'set_cookie', flags=re.IGNORECASE
        )
        
        if not matches:
            return findings
        
        for match in matches:
            # Extract the set_cookie call context (next ~10 lines)
            lines = content.split('\n')
            start_line = max(0, match.line_number - 1)
            end_line = min(len(lines), match.line_number + 10)
            cookie_context = '\n'.join(lines[start_line:end_line])
            
            # Check for httponly flag
            has_httponly = bool(re.search(
                r'httponly\s*=\s*True',
                cookie_context,
                re.IGNORECASE
            ))
            
            if not has_httponly:
                finding_id = f"auth-no-httponly-{file_path}-{match.line_number}"
                severity = Severity.HIGH
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Missing HttpOnly Flag on Cookie",
                    description=(
                        "Cookie is set without the HttpOnly flag. This makes the cookie "
                        "accessible to JavaScript, increasing the risk of XSS attacks "
                        "stealing session tokens."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Always set httponly=True for session cookies to prevent "
                        "JavaScript access. This protects against XSS-based session theft."
                    ),
                    remediation_code=(
                        "response.set_cookie(\n"
                        "    key='session_id',\n"
                        "    value=session_id,\n"
                        "    httponly=True,  # Prevent JavaScript access\n"
                        "    secure=True,\n"
                        "    samesite='lax'\n"
                        ")"
                    ),
                    cwe_id="CWE-1004",
                    owasp_category="A05:2021 - Security Misconfiguration",
                    references=[
                        "https://owasp.org/www-community/HttpOnly",
                        "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
            
            # Check for secure flag (especially important in production)
            has_secure_false = bool(re.search(
                r'secure\s*=\s*False',
                cookie_context,
                re.IGNORECASE
            ))
            
            if has_secure_false:
                finding_id = f"auth-insecure-cookie-{file_path}-{match.line_number}"
                severity = self.severity_calculator.calculate_severity("insecure_cookie_config")
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Insecure Cookie Configuration (secure=False)",
                    description=(
                        "Cookie is explicitly set with secure=False. This allows the cookie "
                        "to be transmitted over unencrypted HTTP connections, making it "
                        "vulnerable to interception by network attackers (man-in-the-middle)."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Set secure=True for all session cookies in production. This ensures "
                        "cookies are only transmitted over HTTPS. For development, use "
                        "environment-based configuration."
                    ),
                    remediation_code=(
                        "import os\n\n"
                        "response.set_cookie(\n"
                        "    key='session_id',\n"
                        "    value=session_id,\n"
                        "    httponly=True,\n"
                        "    secure=os.getenv('ENV') == 'production',  # True in production\n"
                        "    samesite='lax'\n"
                        ")"
                    ),
                    cwe_id="CWE-614",
                    owasp_category="A05:2021 - Security Misconfiguration",
                    references=[
                        "https://owasp.org/www-community/controls/SecureCookieAttribute",
                        "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
            
            # Check for samesite attribute
            has_samesite = bool(re.search(
                r'samesite\s*=\s*["\']?(strict|lax)["\']?',
                cookie_context,
                re.IGNORECASE
            ))
            
            if not has_samesite:
                finding_id = f"auth-no-samesite-{file_path}-{match.line_number}"
                severity = Severity.MEDIUM
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Missing SameSite Attribute on Cookie",
                    description=(
                        "Cookie is set without the SameSite attribute. This makes the "
                        "application vulnerable to Cross-Site Request Forgery (CSRF) attacks "
                        "as the cookie will be sent with cross-site requests."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Set samesite='lax' or samesite='strict' for session cookies:\n"
                        "- 'strict': Cookie only sent for same-site requests (most secure)\n"
                        "- 'lax': Cookie sent for top-level navigation (recommended)\n"
                        "- 'none': Cookie sent with all requests (requires secure=True)"
                    ),
                    remediation_code=(
                        "response.set_cookie(\n"
                        "    key='session_id',\n"
                        "    value=session_id,\n"
                        "    httponly=True,\n"
                        "    secure=True,\n"
                        "    samesite='lax'  # Protect against CSRF\n"
                        ")"
                    ),
                    cwe_id="CWE-352",
                    owasp_category="A01:2021 - Broken Access Control",
                    references=[
                        "https://owasp.org/www-community/SameSite",
                        "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
            
            # Check for max_age or expires
            has_expiration = bool(re.search(
                r'(max_age|expires)\s*=',
                cookie_context,
                re.IGNORECASE
            ))
            
            if not has_expiration:
                finding_id = f"auth-no-cookie-expiry-{file_path}-{match.line_number}"
                severity = Severity.LOW
                confidence = Confidence.MEDIUM
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Missing Cookie Expiration",
                    description=(
                        "Session cookie is set without an explicit expiration time. "
                        "Without max_age or expires, the cookie becomes a session cookie "
                        "that persists until the browser is closed, which may not align "
                        "with security requirements."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Set an explicit max_age for session cookies. Recommended values:\n"
                        "- Short sessions: 15-30 minutes (900-1800 seconds)\n"
                        "- Standard sessions: 1-4 hours (3600-14400 seconds)\n"
                        "- Extended sessions: 24 hours (86400 seconds)\n"
                        "Align cookie expiration with server-side session expiration."
                    ),
                    remediation_code=(
                        "response.set_cookie(\n"
                        "    key='session_id',\n"
                        "    value=session_id,\n"
                        "    httponly=True,\n"
                        "    secure=True,\n"
                        "    samesite='lax',\n"
                        "    max_age=3600  # 1 hour in seconds\n"
                        ")"
                    ),
                    cwe_id="CWE-613",
                    owasp_category="A07:2021 - Identification and Authentication Failures",
                    references=[
                        "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        return findings
