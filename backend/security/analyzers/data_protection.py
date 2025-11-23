"""Data protection security analyzer for detecting data security vulnerabilities."""

import re
from typing import List
from backend.security.analyzers.base import BaseAnalyzer
from backend.security.models.finding import Finding, Severity, Confidence
from backend.security.utils.pattern_matcher import PatternMatcher
from backend.security.utils.ast_parser import ASTParser
from backend.security.utils.severity import SeverityCalculator


class DataProtectionAnalyzer(BaseAnalyzer):
    """
    Analyzer for data protection and privacy vulnerabilities.
    
    Detects issues including:
    - SQL injection vulnerabilities (string concatenation in queries)
    - Unparameterized database queries
    - Raw SQL execution with user input
    - Sensitive data exposure (passwords, API keys in responses/logs)
    - Secrets in log statements
    - Sensitive data in error messages
    - Missing input sanitization
    - XSS vulnerabilities in user input handling
    - Command injection risks
    """
    
    def __init__(self):
        """Initialize data protection analyzer."""
        super().__init__()
        self.pattern_matcher = PatternMatcher(context_lines=3)
        self.ast_parser = ASTParser()
        self.severity_calculator = SeverityCalculator()
    
    def get_category(self) -> str:
        """Return the security category."""
        return "data_protection"
    
    def analyze(self, file_path: str, content: str) -> List[Finding]:
        """
        Analyze a file for data protection vulnerabilities.
        
        Args:
            file_path: Relative path to the file
            content: File content
            
        Returns:
            List of security findings
        """
        findings = []
        
        # Check for SQL injection vulnerabilities
        findings.extend(self._check_sql_injection(file_path, content))
        
        # Check for sensitive data exposure
        findings.extend(self._check_sensitive_data_exposure(file_path, content))
        
        # Check for input validation issues
        findings.extend(self._check_input_validation(file_path, content))
        
        return findings
    
    def _check_sql_injection(self, file_path: str, content: str) -> List[Finding]:
        """Check for SQL injection vulnerabilities."""
        findings = []
        
        # Pattern 1: String concatenation in SQL queries with f-strings
        f_string_sql_patterns = [
            (r'f["\'].*SELECT.*\{.*\}', 'f_string_sql'),
            (r'f["\'].*INSERT.*\{.*\}', 'f_string_sql'),
            (r'f["\'].*UPDATE.*\{.*\}', 'f_string_sql'),
            (r'f["\'].*DELETE.*\{.*\}', 'f_string_sql'),
            (r'f["\'].*WHERE.*\{.*\}', 'f_string_sql'),
        ]
        
        for pattern, pattern_name in f_string_sql_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                finding_id = f"data-sql-injection-fstring-{file_path}-{match.line_number}"
                severity = self.severity_calculator.calculate_severity("sql_injection")
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="SQL Injection via F-String Formatting",
                    description=(
                        f"SQL query uses f-string formatting which can lead to SQL injection "
                        f"vulnerabilities. User input embedded in SQL queries via string "
                        f"formatting allows attackers to manipulate the query structure.\n\n"
                        f"Found: {match.matched_text}"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Use parameterized queries or ORM methods instead of string formatting:\n"
                        "1. For SQLAlchemy ORM: Use filter() with bound parameters\n"
                        "2. For raw SQL: Use parameter binding with :param syntax\n"
                        "3. Never concatenate user input directly into SQL queries\n"
                        "4. Use prepared statements for all database operations"
                    ),
                    remediation_code=(
                        "# Instead of:\n"
                        "query = f\"SELECT * FROM users WHERE id = {user_id}\"\n"
                        "db.execute(query)\n\n"
                        "# Use ORM:\n"
                        "user = db.query(User).filter(User.id == user_id).first()\n\n"
                        "# Or parameterized query:\n"
                        "query = text(\"SELECT * FROM users WHERE id = :user_id\")\n"
                        "db.execute(query, {'user_id': user_id})"
                    ),
                    cwe_id="CWE-89",
                    owasp_category="A03:2021 - Injection",
                    references=[
                        "https://owasp.org/Top10/A03_2021-Injection/",
                        "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Pattern 2: String concatenation with + operator in SQL
        concat_sql_patterns = [
            (r'["\']SELECT[^"\']*["\'][\s]*\+', 'concat_sql'),
            (r'["\']INSERT[^"\']*["\'][\s]*\+', 'concat_sql'),
            (r'["\']UPDATE[^"\']*["\'][\s]*\+', 'concat_sql'),
            (r'["\']DELETE[^"\']*["\'][\s]*\+', 'concat_sql'),
            (r'["\']WHERE[^"\']*["\'][\s]*\+', 'concat_sql'),
        ]
        
        for pattern, pattern_name in concat_sql_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                finding_id = f"data-sql-injection-concat-{file_path}-{match.line_number}"
                severity = self.severity_calculator.calculate_severity("sql_injection")
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="SQL Injection via String Concatenation",
                    description=(
                        f"SQL query uses string concatenation which can lead to SQL injection "
                        f"vulnerabilities. Concatenating user input into SQL queries allows "
                        f"attackers to inject malicious SQL code.\n\n"
                        f"Found: {match.matched_text}"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Replace string concatenation with parameterized queries:\n"
                        "1. Use SQLAlchemy ORM filter methods\n"
                        "2. Use text() with bound parameters for raw SQL\n"
                        "3. Never build SQL queries by concatenating strings\n"
                        "4. Validate and sanitize all user input"
                    ),
                    remediation_code=(
                        "# Instead of:\n"
                        "query = \"SELECT * FROM users WHERE name = '\" + username + \"'\"\n"
                        "db.execute(query)\n\n"
                        "# Use:\n"
                        "from sqlalchemy import text\n"
                        "query = text(\"SELECT * FROM users WHERE name = :username\")\n"
                        "db.execute(query, {'username': username})"
                    ),
                    cwe_id="CWE-89",
                    owasp_category="A03:2021 - Injection",
                    references=[
                        "https://owasp.org/Top10/A03_2021-Injection/",
                        "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Pattern 3: .format() method in SQL queries
        format_sql_patterns = [
            (r'["\'].*SELECT.*["\']\.format\s*\(', 'format_sql'),
            (r'["\'].*INSERT.*["\']\.format\s*\(', 'format_sql'),
            (r'["\'].*UPDATE.*["\']\.format\s*\(', 'format_sql'),
            (r'["\'].*DELETE.*["\']\.format\s*\(', 'format_sql'),
            (r'["\'].*WHERE.*["\']\.format\s*\(', 'format_sql'),
        ]
        
        for pattern, pattern_name in format_sql_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                finding_id = f"data-sql-injection-format-{file_path}-{match.line_number}"
                severity = self.severity_calculator.calculate_severity("sql_injection")
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="SQL Injection via .format() Method",
                    description=(
                        f"SQL query uses .format() method which can lead to SQL injection "
                        f"vulnerabilities. String formatting methods allow user input to be "
                        f"embedded directly into SQL queries.\n\n"
                        f"Found: {match.matched_text}"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Use parameterized queries instead of .format():\n"
                        "1. Replace .format() with parameter binding\n"
                        "2. Use SQLAlchemy ORM methods when possible\n"
                        "3. For raw SQL, use text() with named parameters\n"
                        "4. Never trust user input in SQL queries"
                    ),
                    remediation_code=(
                        "# Instead of:\n"
                        "query = \"SELECT * FROM users WHERE id = {}\".format(user_id)\n"
                        "db.execute(query)\n\n"
                        "# Use:\n"
                        "from sqlalchemy import text\n"
                        "query = text(\"SELECT * FROM users WHERE id = :user_id\")\n"
                        "db.execute(query, {'user_id': user_id})"
                    ),
                    cwe_id="CWE-89",
                    owasp_category="A03:2021 - Injection",
                    references=[
                        "https://owasp.org/Top10/A03_2021-Injection/",
                        "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Pattern 4: % string formatting in SQL queries
        percent_sql_patterns = [
            (r'["\'].*SELECT.*%[sd]', 'percent_sql'),
            (r'["\'].*INSERT.*%[sd]', 'percent_sql'),
            (r'["\'].*UPDATE.*%[sd]', 'percent_sql'),
            (r'["\'].*DELETE.*%[sd]', 'percent_sql'),
            (r'["\'].*WHERE.*%[sd]', 'percent_sql'),
        ]
        
        for pattern, pattern_name in percent_sql_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                finding_id = f"data-sql-injection-percent-{file_path}-{match.line_number}"
                severity = self.severity_calculator.calculate_severity("sql_injection")
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="SQL Injection via % String Formatting",
                    description=(
                        f"SQL query uses % string formatting which can lead to SQL injection "
                        f"vulnerabilities. Old-style string formatting allows user input to be "
                        f"embedded directly into SQL queries.\n\n"
                        f"Found: {match.matched_text}"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Replace % formatting with parameterized queries:\n"
                        "1. Use SQLAlchemy ORM filter methods\n"
                        "2. Use text() with bound parameters for raw SQL\n"
                        "3. Never use % formatting for SQL queries\n"
                        "4. Implement input validation and sanitization"
                    ),
                    remediation_code=(
                        "# Instead of:\n"
                        "query = \"SELECT * FROM users WHERE name = '%s'\" % username\n"
                        "db.execute(query)\n\n"
                        "# Use:\n"
                        "from sqlalchemy import text\n"
                        "query = text(\"SELECT * FROM users WHERE name = :username\")\n"
                        "db.execute(query, {'username': username})"
                    ),
                    cwe_id="CWE-89",
                    owasp_category="A03:2021 - Injection",
                    references=[
                        "https://owasp.org/Top10/A03_2021-Injection/",
                        "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Pattern 5: Raw SQL execution with execute() and potential user input
        execute_patterns = [
            (r'\.execute\s*\(\s*f["\']', 'execute_fstring'),
            (r'\.execute\s*\(\s*["\'][^"\']*["\'][\s]*\+', 'execute_concat'),
            (r'\.execute\s*\(\s*["\'][^"\']*["\']\.format', 'execute_format'),
        ]
        
        for pattern, pattern_name in execute_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name
            )
            
            for match in matches:
                finding_id = f"data-raw-sql-exec-{file_path}-{match.line_number}"
                severity = self.severity_calculator.calculate_severity("sql_injection")
                confidence = Confidence.MEDIUM
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Raw SQL Execution with String Formatting",
                    description=(
                        f"Raw SQL execution detected with string formatting. This pattern "
                        f"is highly susceptible to SQL injection if user input is involved.\n\n"
                        f"Found: {match.matched_text}"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Use parameterized queries for all raw SQL execution:\n"
                        "1. Replace string formatting with parameter binding\n"
                        "2. Use text() with named parameters\n"
                        "3. Prefer ORM methods over raw SQL when possible\n"
                        "4. Validate all input before database operations"
                    ),
                    remediation_code=(
                        "# Instead of:\n"
                        "db.execute(f\"SELECT * FROM users WHERE id = {user_id}\")\n\n"
                        "# Use:\n"
                        "from sqlalchemy import text\n"
                        "db.execute(text(\"SELECT * FROM users WHERE id = :user_id\"), {'user_id': user_id})"
                    ),
                    cwe_id="CWE-89",
                    owasp_category="A03:2021 - Injection",
                    references=[
                        "https://owasp.org/Top10/A03_2021-Injection/",
                        "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        return findings

    def _check_sensitive_data_exposure(self, file_path: str, content: str) -> List[Finding]:
        """Check for sensitive data exposure in responses and logs."""
        findings = []
        
        # Pattern 1: password_hash in API response models (schemas)
        if '/schemas/' in file_path or 'schema' in file_path.lower():
            password_hash_patterns = [
                (r'password_hash\s*:\s*str', 'password_hash_field'),
                (r'password_hash\s*=\s*Field', 'password_hash_field'),
                (r'["\']password_hash["\']', 'password_hash_string'),
            ]
            
            for pattern, pattern_name in password_hash_patterns:
                matches = self.pattern_matcher.match_pattern(
                    pattern, content, pattern_name
                )
                
                for match in matches:
                    # Check if this is in a response model (not excluded)
                    lines = content.split('\n')
                    start_line = max(0, match.line_number - 10)
                    end_line = min(len(lines), match.line_number + 5)
                    context = '\n'.join(lines[start_line:end_line])
                    
                    # Check if it's explicitly excluded
                    is_excluded = bool(re.search(
                        r'exclude\s*=\s*\{[^}]*["\']password_hash["\']',
                        context
                    ))
                    
                    if not is_excluded:
                        finding_id = f"data-password-hash-exposure-{file_path}-{match.line_number}"
                        severity = Severity.CRITICAL
                        confidence = Confidence.HIGH
                        
                        findings.append(Finding(
                            id=finding_id,
                            category=self.get_category(),
                            title="Password Hash Exposed in API Response",
                            description=(
                                f"password_hash field detected in API response model. "
                                f"Password hashes should never be included in API responses "
                                f"as they can be used for offline cracking attacks.\n\n"
                                f"Found: {match.matched_text}"
                            ),
                            severity=severity,
                            confidence=confidence,
                            file_path=file_path,
                            line_number=match.line_number,
                            code_snippet=match.code_snippet,
                            remediation=(
                                "Remove password_hash from API response models:\n"
                                "1. Exclude password_hash in model_config\n"
                                "2. Create separate response schemas without sensitive fields\n"
                                "3. Use model_dump(exclude={'password_hash'}) when needed\n"
                                "4. Never return password hashes to clients"
                            ),
                            remediation_code=(
                                "# In Pydantic v2:\n"
                                "class UserResponse(BaseModel):\n"
                                "    model_config = ConfigDict(\n"
                                "        from_attributes=True,\n"
                                "        exclude={'password_hash'}  # Exclude sensitive field\n"
                                "    )\n"
                                "    id: int\n"
                                "    email: str\n"
                                "    # password_hash: str  # Remove this field"
                            ),
                            cwe_id="CWE-200",
                            owasp_category="A01:2021 - Broken Access Control",
                            references=[
                                "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
                                "https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html"
                            ],
                            detected_by=self.get_name()
                        ))
        
        # Pattern 2: API keys or secrets in response models
        secret_field_patterns = [
            (r'api_key\s*:\s*str', 'api_key_field'),
            (r'secret\s*:\s*str', 'secret_field'),
            (r'token\s*:\s*str', 'token_field'),
            (r'private_key\s*:\s*str', 'private_key_field'),
        ]
        
        if '/schemas/' in file_path or 'schema' in file_path.lower():
            for pattern, pattern_name in secret_field_patterns:
                matches = self.pattern_matcher.match_pattern(
                    pattern, content, pattern_name
                )
                
                for match in matches:
                    # Check context to see if it's in a response model
                    lines = content.split('\n')
                    start_line = max(0, match.line_number - 10)
                    end_line = min(len(lines), match.line_number + 5)
                    context = '\n'.join(lines[start_line:end_line])
                    
                    # Skip if it's in a request model or explicitly for creation
                    is_request = bool(re.search(
                        r'(Request|Create|Update)',
                        context
                    ))
                    
                    if not is_request:
                        finding_id = f"data-secret-exposure-{file_path}-{match.line_number}"
                        severity = Severity.HIGH
                        confidence = Confidence.MEDIUM
                        
                        findings.append(Finding(
                            id=finding_id,
                            category=self.get_category(),
                            title="Sensitive Field in API Response Model",
                            description=(
                                f"Sensitive field detected in API response model. "
                                f"Fields like api_key, secret, token, or private_key should "
                                f"not be included in API responses.\n\n"
                                f"Found: {match.matched_text}"
                            ),
                            severity=severity,
                            confidence=confidence,
                            file_path=file_path,
                            line_number=match.line_number,
                            code_snippet=match.code_snippet,
                            remediation=(
                                "Remove sensitive fields from response models:\n"
                                "1. Create separate response schemas without secrets\n"
                                "2. Only return masked or partial values if needed\n"
                                "3. Use exclude in model_config for sensitive fields\n"
                                "4. Return only the minimum necessary data"
                            ),
                            remediation_code=(
                                "# Create separate response model:\n"
                                "class APIKeyResponse(BaseModel):\n"
                                "    id: int\n"
                                "    name: str\n"
                                "    key_preview: str  # Only last 4 chars: '...xyz'\n"
                                "    created_at: datetime\n"
                                "    # api_key: str  # Never include full key"
                            ),
                            cwe_id="CWE-200",
                            owasp_category="A01:2021 - Broken Access Control",
                            references=[
                                "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
                                "https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html"
                            ],
                            detected_by=self.get_name()
                        ))
        
        # Pattern 3: Secrets in log statements
        log_patterns = [
            (r'log(?:ger)?\.(?:debug|info|warning|error)\s*\([^)]*(?:password|secret|token|api_key)', 'log_secret'),
            (r'print\s*\([^)]*(?:password|secret|token|api_key)', 'print_secret'),
            (r'logging\.(?:debug|info|warning|error)\s*\([^)]*(?:password|secret|token|api_key)', 'logging_secret'),
        ]
        
        for pattern, pattern_name in log_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                finding_id = f"data-secret-in-logs-{file_path}-{match.line_number}"
                severity = Severity.HIGH
                confidence = Confidence.MEDIUM
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Sensitive Data in Log Statement",
                    description=(
                        f"Log statement may contain sensitive data such as passwords, "
                        f"secrets, tokens, or API keys. Logging sensitive data can lead "
                        f"to credential exposure through log files.\n\n"
                        f"Found: {match.matched_text}"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Remove sensitive data from log statements:\n"
                        "1. Never log passwords, tokens, or API keys\n"
                        "2. Mask or redact sensitive values if logging is necessary\n"
                        "3. Use structured logging with field filtering\n"
                        "4. Review all log statements for sensitive data"
                    ),
                    remediation_code=(
                        "# Instead of:\n"
                        "logger.info(f\"User login: {username} with password {password}\")\n\n"
                        "# Use:\n"
                        "logger.info(f\"User login: {username}\")  # No password\n\n"
                        "# Or mask sensitive data:\n"
                        "def mask_secret(secret: str) -> str:\n"
                        "    return secret[:4] + '***' if len(secret) > 4 else '***'\n\n"
                        "logger.info(f\"API key: {mask_secret(api_key)}\")"
                    ),
                    cwe_id="CWE-532",
                    owasp_category="A09:2021 - Security Logging and Monitoring Failures",
                    references=[
                        "https://owasp.org/Top10/A09_2021-Security_Logging_and_Monitoring_Failures/",
                        "https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Pattern 4: Sensitive data in error messages
        error_patterns = [
            (r'raise\s+\w+Exception\s*\([^)]*(?:password|secret|token|api_key)', 'error_secret'),
            (r'HTTPException\s*\([^)]*(?:password|secret|token|api_key)', 'http_error_secret'),
        ]
        
        for pattern, pattern_name in error_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                finding_id = f"data-secret-in-error-{file_path}-{match.line_number}"
                severity = Severity.MEDIUM
                confidence = Confidence.LOW
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Potential Sensitive Data in Error Message",
                    description=(
                        f"Error message may contain sensitive data. Error messages "
                        f"should not expose passwords, secrets, tokens, or API keys "
                        f"as they may be logged or displayed to users.\n\n"
                        f"Found: {match.matched_text}"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Remove sensitive data from error messages:\n"
                        "1. Use generic error messages for authentication failures\n"
                        "2. Never include credentials in exception messages\n"
                        "3. Log detailed errors server-side, show generic messages to users\n"
                        "4. Review all exception handling for data exposure"
                    ),
                    remediation_code=(
                        "# Instead of:\n"
                        "raise HTTPException(401, f\"Invalid password: {password}\")\n\n"
                        "# Use:\n"
                        "raise HTTPException(401, \"Invalid credentials\")\n"
                        "# Log details server-side only:\n"
                        "logger.warning(f\"Failed login attempt for user {username}\")"
                    ),
                    cwe_id="CWE-209",
                    owasp_category="A04:2021 - Insecure Design",
                    references=[
                        "https://owasp.org/Top10/A04_2021-Insecure_Design/",
                        "https://cwe.mitre.org/data/definitions/209.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        return findings
    
    def _check_input_validation(self, file_path: str, content: str) -> List[Finding]:
        """Check for input validation and sanitization issues."""
        findings = []
        
        # Pattern 1: HTMLResponse with user input (XSS risk)
        html_response_patterns = [
            (r'HTMLResponse\s*\([^)]*\{', 'html_response_fstring'),
            (r'HTMLResponse\s*\([^)]*\+', 'html_response_concat'),
            (r'HTMLResponse\s*\([^)]*\.format', 'html_response_format'),
        ]
        
        for pattern, pattern_name in html_response_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name
            )
            
            for match in matches:
                finding_id = f"data-xss-html-response-{file_path}-{match.line_number}"
                severity = Severity.HIGH
                confidence = Confidence.MEDIUM
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Potential XSS in HTMLResponse",
                    description=(
                        f"HTMLResponse with dynamic content detected. If user input is "
                        f"included in HTML responses without proper escaping, it can lead "
                        f"to Cross-Site Scripting (XSS) vulnerabilities.\n\n"
                        f"Found: {match.matched_text}"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Prevent XSS in HTML responses:\n"
                        "1. Use template engines with auto-escaping (Jinja2)\n"
                        "2. Escape all user input with html.escape()\n"
                        "3. Use Content-Security-Policy headers\n"
                        "4. Prefer JSON responses over HTML when possible\n"
                        "5. Validate and sanitize all user input"
                    ),
                    remediation_code=(
                        "# Instead of:\n"
                        "return HTMLResponse(f\"<h1>Hello {username}</h1>\")\n\n"
                        "# Use template with auto-escaping:\n"
                        "from fastapi.templating import Jinja2Templates\n"
                        "templates = Jinja2Templates(directory=\"templates\")\n"
                        "return templates.TemplateResponse(\"page.html\", {\"username\": username})\n\n"
                        "# Or escape manually:\n"
                        "import html\n"
                        "safe_username = html.escape(username)\n"
                        "return HTMLResponse(f\"<h1>Hello {safe_username}</h1>\")"
                    ),
                    cwe_id="CWE-79",
                    owasp_category="A03:2021 - Injection",
                    references=[
                        "https://owasp.org/Top10/A03_2021-Injection/",
                        "https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Pattern 2: Command injection via subprocess/os.system
        command_injection_patterns = [
            (r'subprocess\.(?:call|run|Popen)\s*\([^)]*\{', 'subprocess_fstring'),
            (r'subprocess\.(?:call|run|Popen)\s*\([^)]*\+', 'subprocess_concat'),
            (r'subprocess\.(?:call|run|Popen)\s*\([^)]*\.format', 'subprocess_format'),
            (r'os\.system\s*\([^)]*\{', 'os_system_fstring'),
            (r'os\.system\s*\([^)]*\+', 'os_system_concat'),
            (r'os\.system\s*\([^)]*\.format', 'os_system_format'),
        ]
        
        for pattern, pattern_name in command_injection_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name
            )
            
            for match in matches:
                finding_id = f"data-command-injection-{file_path}-{match.line_number}"
                severity = Severity.CRITICAL
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Command Injection Vulnerability",
                    description=(
                        f"Command execution with string formatting detected. If user input "
                        f"is included in shell commands, attackers can inject arbitrary "
                        f"commands leading to complete system compromise.\n\n"
                        f"Found: {match.matched_text}"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Prevent command injection:\n"
                        "1. Never use shell=True with user input\n"
                        "2. Use subprocess with list arguments, not strings\n"
                        "3. Validate and whitelist allowed commands/arguments\n"
                        "4. Use Python libraries instead of shell commands when possible\n"
                        "5. Implement strict input validation"
                    ),
                    remediation_code=(
                        "# Instead of:\n"
                        "os.system(f\"ls {user_directory}\")\n"
                        "subprocess.run(f\"cat {filename}\", shell=True)\n\n"
                        "# Use:\n"
                        "import subprocess\n"
                        "# Pass arguments as list, not string:\n"
                        "subprocess.run(['ls', user_directory], shell=False)\n"
                        "subprocess.run(['cat', filename], shell=False)\n\n"
                        "# Better: use Python libraries:\n"
                        "import os\n"
                        "files = os.listdir(user_directory)\n"
                        "with open(filename, 'r') as f:\n"
                        "    content = f.read()"
                    ),
                    cwe_id="CWE-78",
                    owasp_category="A03:2021 - Injection",
                    references=[
                        "https://owasp.org/Top10/A03_2021-Injection/",
                        "https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Pattern 3: Missing input sanitization in file operations
        file_operation_patterns = [
            (r'open\s*\([^)]*\{', 'open_fstring'),
            (r'open\s*\([^)]*\+', 'open_concat'),
            (r'open\s*\([^)]*\.format', 'open_format'),
        ]
        
        for pattern, pattern_name in file_operation_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name
            )
            
            for match in matches:
                finding_id = f"data-path-traversal-{file_path}-{match.line_number}"
                severity = Severity.HIGH
                confidence = Confidence.MEDIUM
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Potential Path Traversal Vulnerability",
                    description=(
                        f"File operation with dynamic path detected. If user input is used "
                        f"to construct file paths without validation, attackers can access "
                        f"files outside the intended directory using path traversal (../).\n\n"
                        f"Found: {match.matched_text}"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Prevent path traversal attacks:\n"
                        "1. Validate and sanitize all file paths\n"
                        "2. Use os.path.basename() to strip directory components\n"
                        "3. Use os.path.abspath() and check it starts with allowed directory\n"
                        "4. Whitelist allowed file extensions and names\n"
                        "5. Never trust user-provided file paths directly"
                    ),
                    remediation_code=(
                        "# Instead of:\n"
                        "with open(f\"/uploads/{user_filename}\", 'r') as f:\n"
                        "    content = f.read()\n\n"
                        "# Use:\n"
                        "import os\n"
                        "from pathlib import Path\n\n"
                        "# Sanitize filename:\n"
                        "safe_filename = os.path.basename(user_filename)\n"
                        "base_dir = Path('/uploads').resolve()\n"
                        "file_path = (base_dir / safe_filename).resolve()\n\n"
                        "# Verify path is within allowed directory:\n"
                        "if not str(file_path).startswith(str(base_dir)):\n"
                        "    raise ValueError('Invalid file path')\n\n"
                        "with open(file_path, 'r') as f:\n"
                        "    content = f.read()"
                    ),
                    cwe_id="CWE-22",
                    owasp_category="A01:2021 - Broken Access Control",
                    references=[
                        "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
                        "https://owasp.org/www-community/attacks/Path_Traversal"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Pattern 4: eval() or exec() with user input
        eval_patterns = [
            (r'eval\s*\(', 'eval_usage'),
            (r'exec\s*\(', 'exec_usage'),
        ]
        
        for pattern, pattern_name in eval_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name
            )
            
            for match in matches:
                finding_id = f"data-code-injection-{file_path}-{match.line_number}"
                severity = Severity.CRITICAL
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Code Injection via eval()/exec()",
                    description=(
                        f"Use of eval() or exec() detected. These functions execute arbitrary "
                        f"Python code and should never be used with user input. They can lead "
                        f"to complete system compromise.\n\n"
                        f"Found: {match.matched_text}"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Remove eval() and exec() usage:\n"
                        "1. Never use eval() or exec() with user input\n"
                        "2. Use safer alternatives like ast.literal_eval() for data\n"
                        "3. Use proper parsing libraries for expressions\n"
                        "4. Redesign functionality to avoid dynamic code execution\n"
                        "5. If absolutely necessary, implement strict sandboxing"
                    ),
                    remediation_code=(
                        "# Instead of:\n"
                        "result = eval(user_expression)\n\n"
                        "# For literal data structures, use:\n"
                        "import ast\n"
                        "result = ast.literal_eval(user_data)  # Only evaluates literals\n\n"
                        "# For math expressions, use:\n"
                        "import operator\n"
                        "# Implement safe expression parser with whitelist"
                    ),
                    cwe_id="CWE-95",
                    owasp_category="A03:2021 - Injection",
                    references=[
                        "https://owasp.org/Top10/A03_2021-Injection/",
                        "https://cwe.mitre.org/data/definitions/95.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        return findings
