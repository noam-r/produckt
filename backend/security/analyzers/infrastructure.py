"""Infrastructure security analyzer for detecting configuration and deployment vulnerabilities."""

import re
from typing import List
from backend.security.analyzers.base import BaseAnalyzer
from backend.security.models.finding import Finding, Severity, Confidence
from backend.security.utils.pattern_matcher import PatternMatcher
from backend.security.utils.severity import SeverityCalculator


class InfrastructureAnalyzer(BaseAnalyzer):
    """
    Analyzer for infrastructure and configuration security vulnerabilities.
    
    Detects issues including:
    - Hardcoded secrets (API keys, passwords, tokens)
    - Secrets not loaded from environment variables
    - Default credentials
    - Debug mode enabled in production
    - Insecure production settings
    - Verbose error messages in production
    - Sensitive data in log statements
    - Credentials in logs
    """
    
    def __init__(self):
        """Initialize infrastructure analyzer."""
        super().__init__()
        self.pattern_matcher = PatternMatcher(context_lines=3)
        self.severity_calculator = SeverityCalculator()
    
    def get_category(self) -> str:
        """Return the security category."""
        return "infrastructure"
    
    def analyze(self, file_path: str, content: str) -> List[Finding]:
        """
        Analyze a file for infrastructure vulnerabilities.
        
        Args:
            file_path: Relative path to the file
            content: File content
            
        Returns:
            List of security findings
        """
        findings = []
        
        # Check for hardcoded secrets
        findings.extend(self._check_hardcoded_secrets(file_path, content))
        
        # Check for debug mode in production
        findings.extend(self._check_debug_mode(file_path, content))
        
        # Check for insecure production settings
        findings.extend(self._check_production_settings(file_path, content))
        
        # Check for sensitive data in logs
        findings.extend(self._check_logging_security(file_path, content))
        
        return findings

    
    def _check_hardcoded_secrets(self, file_path: str, content: str) -> List[Finding]:
        """Check for hardcoded secrets, API keys, and passwords in code."""
        findings = []
        
        # Skip test files and example files
        if 'test' in file_path.lower() or 'example' in file_path.lower():
            return findings
        
        # Patterns for detecting hardcoded secrets
        secret_patterns = [
            # API keys
            (r'api[_-]?key\s*[=:]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', 'api_key', 'API Key'),
            (r'apikey\s*[=:]\s*["\']([a-zA-Z0-9_\-]{20,})["\']', 'api_key', 'API Key'),
            
            # AWS credentials
            (r'aws[_-]?access[_-]?key[_-]?id\s*[=:]\s*["\']([A-Z0-9]{20})["\']', 'aws_key', 'AWS Access Key'),
            (r'aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*["\']([a-zA-Z0-9/+=]{40})["\']', 'aws_secret', 'AWS Secret Key'),
            
            # Generic secrets
            (r'secret[_-]?key\s*[=:]\s*["\']([a-zA-Z0-9_\-]{16,})["\']', 'secret_key', 'Secret Key'),
            (r'private[_-]?key\s*[=:]\s*["\']([a-zA-Z0-9_\-]{16,})["\']', 'private_key', 'Private Key'),
            
            # Passwords
            (r'password\s*[=:]\s*["\'](?!.*\{.*\})([^"\']{8,})["\']', 'password', 'Password'),
            (r'passwd\s*[=:]\s*["\'](?!.*\{.*\})([^"\']{8,})["\']', 'password', 'Password'),
            (r'pwd\s*[=:]\s*["\'](?!.*\{.*\})([^"\']{8,})["\']', 'password', 'Password'),
            
            # Tokens
            (r'token\s*[=:]\s*["\']([a-zA-Z0-9_\-\.]{20,})["\']', 'token', 'Token'),
            (r'auth[_-]?token\s*[=:]\s*["\']([a-zA-Z0-9_\-\.]{20,})["\']', 'auth_token', 'Auth Token'),
            (r'bearer\s+([a-zA-Z0-9_\-\.]{20,})', 'bearer_token', 'Bearer Token'),
            
            # Database credentials
            (r'db[_-]?password\s*[=:]\s*["\'](?!.*\{.*\})([^"\']{4,})["\']', 'db_password', 'Database Password'),
            (r'database[_-]?url\s*[=:]\s*["\'][^"\']*://[^:]+:([^@]+)@', 'db_url_password', 'Database URL with Password'),
            
            # JWT secrets
            (r'jwt[_-]?secret\s*[=:]\s*["\']([a-zA-Z0-9_\-]{16,})["\']', 'jwt_secret', 'JWT Secret'),
            
            # Encryption keys
            (r'encryption[_-]?key\s*[=:]\s*["\']([a-zA-Z0-9_\-+/=]{16,})["\']', 'encryption_key', 'Encryption Key'),
        ]
        
        for pattern, pattern_name, secret_type in secret_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                # Skip if it's clearly a placeholder or example
                matched_lower = match.matched_text.lower()
                if any(placeholder in matched_lower for placeholder in [
                    'example', 'placeholder', 'your_', 'xxx', '***', 
                    'changeme', 'replace', 'todo', 'fixme', 'dummy',
                    'test123', 'sample', 'default'
                ]):
                    continue
                
                # Skip if it's loading from environment
                if 'os.environ' in match.code_snippet or 'getenv' in match.code_snippet:
                    continue
                
                # Skip if it's in a comment
                line_content = content.split('\n')[match.line_number - 1] if match.line_number else ""
                if line_content.strip().startswith('#'):
                    continue
                
                finding_id = f"infra-hardcoded-secret-{file_path}-{match.line_number}"
                severity = self.severity_calculator.calculate_severity("hardcoded_secrets")
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title=f"Hardcoded {secret_type} Detected",
                    description=(
                        f"A hardcoded {secret_type.lower()} was detected in the source code. "
                        f"Hardcoded secrets pose significant security risks:\n"
                        f"1. Secrets are exposed in version control history\n"
                        f"2. Anyone with code access can see the secrets\n"
                        f"3. Secrets cannot be rotated without code changes\n"
                        f"4. Different environments cannot use different secrets\n"
                        f"5. Secrets may be accidentally shared or leaked"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        f"Remove the hardcoded {secret_type.lower()} and load it from environment variables instead. "
                        f"Use a secrets management system like:\n"
                        f"1. Environment variables (.env files for local development)\n"
                        f"2. AWS Secrets Manager or Parameter Store\n"
                        f"3. HashiCorp Vault\n"
                        f"4. Azure Key Vault\n"
                        f"5. Google Cloud Secret Manager\n\n"
                        f"Never commit secrets to version control."
                    ),
                    remediation_code=(
                        f"import os\n"
                        f"from dotenv import load_dotenv\n\n"
                        f"load_dotenv()\n\n"
                        f"# Load from environment variable\n"
                        f"{pattern_name.upper()} = os.getenv('{pattern_name.upper()}')\n"
                        f"if not {pattern_name.upper()}:\n"
                        f"    raise ValueError('{pattern_name.upper()} environment variable not set')"
                    ),
                    cwe_id="CWE-798",
                    owasp_category="A07:2021 - Identification and Authentication Failures",
                    references=[
                        "https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password",
                        "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Check for secrets not loaded from environment variables
        # Look for direct string assignments that should be from env
        env_var_patterns = [
            (r'SECRET_KEY\s*=\s*["\'](?!.*getenv)([^"\']+)["\']', 'SECRET_KEY'),
            (r'API_KEY\s*=\s*["\'](?!.*getenv)([^"\']+)["\']', 'API_KEY'),
            (r'DATABASE_URL\s*=\s*["\'](?!.*getenv)([^"\']+)["\']', 'DATABASE_URL'),
        ]
        
        for pattern, var_name in env_var_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, f'non_env_{var_name.lower()}'
            )
            
            for match in matches:
                # Skip if it's already using environment variables
                if 'os.environ' in match.code_snippet or 'getenv' in match.code_snippet:
                    continue
                
                finding_id = f"infra-non-env-secret-{file_path}-{match.line_number}"
                severity = Severity.HIGH
                confidence = Confidence.MEDIUM
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title=f"{var_name} Not Loaded from Environment",
                    description=(
                        f"The {var_name} variable is assigned directly in code rather than "
                        f"being loaded from environment variables. This makes it difficult to:\n"
                        f"1. Use different values in different environments\n"
                        f"2. Rotate secrets without code changes\n"
                        f"3. Keep secrets out of version control"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        f"Load {var_name} from environment variables using os.getenv() or "
                        f"a configuration management library."
                    ),
                    remediation_code=(
                        f"import os\n\n"
                        f"{var_name} = os.getenv('{var_name}')\n"
                        f"if not {var_name}:\n"
                        f"    raise ValueError('{var_name} must be set in environment')"
                    ),
                    cwe_id="CWE-798",
                    owasp_category="A05:2021 - Security Misconfiguration",
                    references=[
                        "https://12factor.net/config",
                        "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Check for default credentials
        default_creds_patterns = [
            (r'username\s*[=:]\s*["\']admin["\']', 'default_username'),
            (r'user\s*[=:]\s*["\']admin["\']', 'default_username'),
            (r'password\s*[=:]\s*["\']admin["\']', 'default_password'),
            (r'password\s*[=:]\s*["\']password["\']', 'default_password'),
            (r'password\s*[=:]\s*["\']123456["\']', 'default_password'),
            (r'password\s*[=:]\s*["\']root["\']', 'default_password'),
        ]
        
        for pattern, pattern_name in default_creds_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                # Skip if in test files
                if 'test' in file_path.lower():
                    continue
                
                # Skip if it's in a comment
                line_content = content.split('\n')[match.line_number - 1] if match.line_number else ""
                if line_content.strip().startswith('#'):
                    continue
                
                finding_id = f"infra-default-creds-{file_path}-{match.line_number}"
                severity = Severity.CRITICAL
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Default Credentials Detected",
                    description=(
                        "Default credentials (admin/admin, admin/password, etc.) were detected "
                        "in the code. Default credentials are well-known and are the first thing "
                        "attackers try when attempting to gain unauthorized access. Using default "
                        "credentials in production is a critical security vulnerability."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Never use default credentials. Instead:\n"
                        "1. Generate strong, unique credentials for each environment\n"
                        "2. Store credentials in environment variables or secrets manager\n"
                        "3. Require users to set their own passwords on first login\n"
                        "4. Implement password complexity requirements\n"
                        "5. Force password changes for default accounts"
                    ),
                    remediation_code=(
                        "import os\n"
                        "import secrets\n\n"
                        "# Generate strong random password\n"
                        "password = secrets.token_urlsafe(32)\n\n"
                        "# Or load from environment\n"
                        "username = os.getenv('ADMIN_USERNAME')\n"
                        "password = os.getenv('ADMIN_PASSWORD')\n"
                        "if not username or not password:\n"
                        "    raise ValueError('Admin credentials must be set')"
                    ),
                    cwe_id="CWE-798",
                    owasp_category="A07:2021 - Identification and Authentication Failures",
                    references=[
                        "https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password",
                        "https://cwe.mitre.org/data/definitions/798.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        return findings

    
    def _check_debug_mode(self, file_path: str, content: str) -> List[Finding]:
        """Check for debug mode enabled in production settings."""
        findings = []
        
        # Skip if not a config file
        if not any(keyword in file_path.lower() for keyword in ['config', 'settings', 'main.py', '__init__.py']):
            return findings
        
        # Patterns for debug mode detection
        debug_patterns = [
            (r'debug\s*[=:]\s*True', 'debug_true'),
            (r'DEBUG\s*[=:]\s*True', 'debug_true'),
            (r'app\.debug\s*=\s*True', 'app_debug'),
            (r'reload\s*[=:]\s*True', 'reload_true'),
        ]
        
        for pattern, pattern_name in debug_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name
            )
            
            for match in matches:
                # Check if there's a production check nearby
                context_window = content[max(0, match.line_number - 10):match.line_number + 10]
                has_env_check = bool(re.search(
                    r'(if.*production|if.*PRODUCTION|if.*env.*prod|unless.*dev)',
                    context_window,
                    re.IGNORECASE
                ))
                
                # If there's an environment check, it might be conditional
                if has_env_check:
                    confidence = Confidence.MEDIUM
                else:
                    confidence = Confidence.HIGH
                
                finding_id = f"infra-debug-mode-{file_path}-{match.line_number}"
                severity = self.severity_calculator.calculate_severity("debug_mode_enabled")
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Debug Mode Enabled",
                    description=(
                        "Debug mode is enabled in the application configuration. Running with "
                        "debug mode enabled in production exposes sensitive information:\n"
                        "1. Detailed error messages with stack traces\n"
                        "2. Internal application structure and file paths\n"
                        "3. Source code snippets in error pages\n"
                        "4. Environment variables and configuration details\n"
                        "5. Database query details\n\n"
                        "This information can be used by attackers to identify vulnerabilities "
                        "and plan attacks."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Disable debug mode in production environments. Use environment variables "
                        "to control debug settings:\n"
                        "1. Set debug=False in production\n"
                        "2. Use environment-specific configuration\n"
                        "3. Implement proper error handling and logging\n"
                        "4. Show generic error messages to users\n"
                        "5. Log detailed errors securely for developers"
                    ),
                    remediation_code=(
                        "import os\n\n"
                        "# Load from environment, default to False\n"
                        "DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'\n\n"
                        "# Or use environment-specific settings\n"
                        "ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')\n"
                        "DEBUG = ENVIRONMENT == 'development'"
                    ),
                    cwe_id="CWE-489",
                    owasp_category="A05:2021 - Security Misconfiguration",
                    references=[
                        "https://owasp.org/www-project-top-ten/2017/A6_2017-Security_Misconfiguration",
                        "https://cwe.mitre.org/data/definitions/489.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Check for verbose error messages
        verbose_error_patterns = [
            (r'show_error_details\s*[=:]\s*True', 'verbose_errors'),
            (r'detailed_errors\s*[=:]\s*True', 'verbose_errors'),
            (r'include_traceback\s*[=:]\s*True', 'verbose_errors'),
        ]
        
        for pattern, pattern_name in verbose_error_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                finding_id = f"infra-verbose-errors-{file_path}-{match.line_number}"
                severity = Severity.MEDIUM
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Verbose Error Messages Enabled",
                    description=(
                        "The application is configured to show detailed error messages. "
                        "Verbose error messages can expose sensitive information about the "
                        "application's internal workings, making it easier for attackers to "
                        "identify and exploit vulnerabilities."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Disable verbose error messages in production. Show generic error "
                        "messages to users while logging detailed errors securely for debugging."
                    ),
                    remediation_code=(
                        "# Show generic errors to users\n"
                        "show_error_details = False\n\n"
                        "# Log detailed errors for developers\n"
                        "import logging\n"
                        "logger.error('Detailed error info', exc_info=True)"
                    ),
                    cwe_id="CWE-209",
                    owasp_category="A05:2021 - Security Misconfiguration",
                    references=[
                        "https://owasp.org/www-community/Improper_Error_Handling",
                        "https://cwe.mitre.org/data/definitions/209.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        return findings
    
    def _check_production_settings(self, file_path: str, content: str) -> List[Finding]:
        """Check for insecure production settings."""
        findings = []
        
        # Skip if not a config file
        if not any(keyword in file_path.lower() for keyword in ['config', 'settings', 'main.py']):
            return findings
        
        # Check for insecure cookie settings
        insecure_cookie_patterns = [
            (r'secure\s*[=:]\s*False', 'insecure_cookie', 'secure flag'),
            (r'httponly\s*[=:]\s*False', 'httponly_false', 'httpOnly flag'),
            (r'samesite\s*[=:]\s*["\']?None["\']?', 'samesite_none', 'sameSite attribute'),
        ]
        
        for pattern, pattern_name, setting_name in insecure_cookie_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                # Check if this is in a cookie or session configuration
                if not any(keyword in match.code_snippet.lower() for keyword in ['cookie', 'session']):
                    continue
                
                finding_id = f"infra-insecure-cookie-{file_path}-{match.line_number}"
                severity = Severity.HIGH
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title=f"Insecure Cookie Configuration: {setting_name} Disabled",
                    description=(
                        f"Cookie security setting '{setting_name}' is disabled or set to an insecure value. "
                        f"This exposes the application to various attacks:\n\n"
                        f"- secure=False: Cookies can be transmitted over unencrypted HTTP, "
                        f"allowing interception by attackers\n"
                        f"- httpOnly=False: Cookies can be accessed by JavaScript, enabling XSS attacks "
                        f"to steal session tokens\n"
                        f"- sameSite=None: Cookies are sent with cross-site requests, enabling CSRF attacks"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Enable secure cookie settings in production:\n"
                        "1. secure=True: Ensures cookies are only sent over HTTPS\n"
                        "2. httpOnly=True: Prevents JavaScript access to cookies\n"
                        "3. sameSite='Lax' or 'Strict': Prevents CSRF attacks\n\n"
                        "These settings should always be enabled for session cookies and "
                        "authentication tokens in production."
                    ),
                    remediation_code=(
                        "# Secure cookie configuration\n"
                        "response.set_cookie(\n"
                        "    key='session_id',\n"
                        "    value=session_id,\n"
                        "    secure=True,      # Only send over HTTPS\n"
                        "    httponly=True,    # No JavaScript access\n"
                        "    samesite='Lax',   # CSRF protection\n"
                        "    max_age=3600      # 1 hour expiration\n"
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
        
        # Check for CORS wildcard with credentials
        cors_patterns = [
            (r'allow_origins\s*[=:]\s*\[\s*["\']?\*["\']?\s*\]', 'cors_wildcard'),
            (r'Access-Control-Allow-Origin\s*[=:]\s*["\']?\*["\']?', 'cors_wildcard_header'),
        ]
        
        for pattern, pattern_name in cors_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name
            )
            
            for match in matches:
                # Check if credentials are also allowed
                context = content[max(0, match.line_number - 5):match.line_number + 5]
                has_credentials = bool(re.search(
                    r'allow_credentials\s*[=:]\s*True',
                    context,
                    re.IGNORECASE
                ))
                
                if has_credentials:
                    severity = Severity.CRITICAL
                    title = "CORS Wildcard with Credentials Enabled"
                    description = (
                        "CORS is configured with wildcard origin (*) AND credentials enabled. "
                        "This is a critical security vulnerability that allows any website to "
                        "make authenticated requests to your API, potentially stealing user data "
                        "or performing unauthorized actions."
                    )
                else:
                    severity = Severity.HIGH
                    title = "Overly Permissive CORS Configuration"
                    description = (
                        "CORS is configured with wildcard origin (*), allowing any website to "
                        "make requests to your API. While credentials are not enabled, this "
                        "still exposes your API to potential abuse and data leakage."
                    )
                
                finding_id = f"infra-cors-wildcard-{file_path}-{match.line_number}"
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title=title,
                    description=description,
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Restrict CORS to specific trusted origins:\n"
                        "1. List specific allowed origins instead of using wildcard\n"
                        "2. Never use wildcard (*) with credentials enabled\n"
                        "3. Validate origin headers on the server side\n"
                        "4. Use environment variables for origin configuration"
                    ),
                    remediation_code=(
                        "# Restrict to specific origins\n"
                        "app.add_middleware(\n"
                        "    CORSMiddleware,\n"
                        "    allow_origins=[\n"
                        "        'https://yourdomain.com',\n"
                        "        'https://app.yourdomain.com'\n"
                        "    ],\n"
                        "    allow_credentials=True,\n"
                        "    allow_methods=['GET', 'POST', 'PUT', 'DELETE'],\n"
                        "    allow_headers=['*']\n"
                        ")"
                    ),
                    cwe_id="CWE-942",
                    owasp_category="A05:2021 - Security Misconfiguration",
                    references=[
                        "https://owasp.org/www-community/attacks/CORS_OriginHeaderScrutiny",
                        "https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Check for missing HTTPS enforcement
        https_patterns = [
            (r'ssl_redirect\s*[=:]\s*False', 'ssl_redirect_false'),
            (r'force_https\s*[=:]\s*False', 'force_https_false'),
            (r'SECURE_SSL_REDIRECT\s*[=:]\s*False', 'secure_ssl_redirect_false'),
        ]
        
        for pattern, pattern_name in https_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                finding_id = f"infra-no-https-{file_path}-{match.line_number}"
                severity = Severity.MEDIUM
                confidence = Confidence.MEDIUM
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="HTTPS Enforcement Disabled",
                    description=(
                        "HTTPS enforcement is disabled in the configuration. Without HTTPS "
                        "enforcement, the application may accept unencrypted HTTP connections, "
                        "exposing sensitive data to interception and man-in-the-middle attacks."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Enable HTTPS enforcement in production:\n"
                        "1. Redirect all HTTP requests to HTTPS\n"
                        "2. Use HSTS headers to enforce HTTPS in browsers\n"
                        "3. Ensure all cookies have secure flag set\n"
                        "4. Use HTTPS for all external resources"
                    ),
                    remediation_code=(
                        "# Enable HTTPS redirect\n"
                        "ssl_redirect = True\n\n"
                        "# Add HSTS header\n"
                        "SECURE_HSTS_SECONDS = 31536000  # 1 year\n"
                        "SECURE_HSTS_INCLUDE_SUBDOMAINS = True"
                    ),
                    cwe_id="CWE-319",
                    owasp_category="A02:2021 - Cryptographic Failures",
                    references=[
                        "https://owasp.org/www-community/controls/SecureCookieAttribute",
                        "https://cheatsheetseries.owasp.org/cheatsheets/Transport_Layer_Protection_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        return findings

    
    def _check_logging_security(self, file_path: str, content: str) -> List[Finding]:
        """Check for sensitive data in log statements and overly verbose logging."""
        findings = []
        
        # Patterns for detecting sensitive data in logs
        sensitive_log_patterns = [
            # Password logging
            (r'log(?:ger)?\.(?:debug|info|warning|error|critical)\s*\([^)]*password[^)]*\)', 'log_password', 'password'),
            (r'print\s*\([^)]*password[^)]*\)', 'print_password', 'password'),
            
            # Token/API key logging
            (r'log(?:ger)?\.(?:debug|info|warning|error|critical)\s*\([^)]*(?:token|api[_-]?key)[^)]*\)', 'log_token', 'token/API key'),
            (r'print\s*\([^)]*(?:token|api[_-]?key)[^)]*\)', 'print_token', 'token/API key'),
            
            # Secret logging
            (r'log(?:ger)?\.(?:debug|info|warning|error|critical)\s*\([^)]*secret[^)]*\)', 'log_secret', 'secret'),
            (r'print\s*\([^)]*secret[^)]*\)', 'print_secret', 'secret'),
            
            # Credit card logging
            (r'log(?:ger)?\.(?:debug|info|warning|error|critical)\s*\([^)]*(?:credit[_-]?card|card[_-]?number)[^)]*\)', 'log_cc', 'credit card'),
            
            # SSN logging
            (r'log(?:ger)?\.(?:debug|info|warning|error|critical)\s*\([^)]*(?:ssn|social[_-]?security)[^)]*\)', 'log_ssn', 'SSN'),
            
            # Email/PII logging
            (r'log(?:ger)?\.(?:debug|info|warning|error|critical)\s*\([^)]*(?:email|phone|address)[^)]*\)', 'log_pii', 'PII'),
        ]
        
        for pattern, pattern_name, data_type in sensitive_log_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                # Skip if it's clearly just a message string, not actual data
                if re.search(r'["\'].*(?:password|token|secret).*["\']', match.matched_text, re.IGNORECASE):
                    # Check if it's logging the actual value (has variable or f-string)
                    has_variable = bool(re.search(r'[{%]|,\s*\w+|f["\']', match.matched_text))
                    if not has_variable:
                        continue
                
                finding_id = f"infra-log-sensitive-{file_path}-{match.line_number}"
                severity = self.severity_calculator.calculate_severity("sensitive_data_in_logs")
                confidence = Confidence.MEDIUM
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title=f"Sensitive Data ({data_type}) in Log Statement",
                    description=(
                        f"A log statement appears to include sensitive data ({data_type}). "
                        f"Logging sensitive information creates several security risks:\n"
                        f"1. Sensitive data stored in log files can be accessed by unauthorized users\n"
                        f"2. Log files are often stored without encryption\n"
                        f"3. Logs may be sent to third-party services or aggregators\n"
                        f"4. Log retention policies may keep sensitive data longer than necessary\n"
                        f"5. Logs may be included in backups or debugging dumps\n\n"
                        f"Even if logs are secured, it's best practice to never log sensitive data."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        f"Remove {data_type} from log statements. Instead:\n"
                        f"1. Log only non-sensitive identifiers (user ID, not password)\n"
                        f"2. Redact or mask sensitive data if logging is necessary\n"
                        f"3. Use structured logging with field-level filtering\n"
                        f"4. Implement log sanitization before writing\n"
                        f"5. Review all log statements for sensitive data"
                    ),
                    remediation_code=(
                        f"# Bad: Logging sensitive data\n"
                        f"# logger.info(f'User login: {{username}} with password {{password}}')\n\n"
                        f"# Good: Log only non-sensitive identifiers\n"
                        f"logger.info(f'User login attempt: {{user_id}}')\n\n"
                        f"# If you must log, redact sensitive parts\n"
                        f"logger.info(f'Token: {{token[:8]}}...')"
                    ),
                    cwe_id="CWE-532",
                    owasp_category="A09:2021 - Security Logging and Monitoring Failures",
                    references=[
                        "https://owasp.org/www-community/vulnerabilities/Information_exposure_through_query_strings_in_url",
                        "https://cwe.mitre.org/data/definitions/532.html",
                        "https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Check for logging entire request/response objects
        object_log_patterns = [
            (r'log(?:ger)?\.(?:debug|info)\s*\([^)]*request[^)]*\)', 'log_request'),
            (r'log(?:ger)?\.(?:debug|info)\s*\([^)]*response[^)]*\)', 'log_response'),
            (r'print\s*\(request\)', 'print_request'),
        ]
        
        for pattern, pattern_name in object_log_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                finding_id = f"infra-log-object-{file_path}-{match.line_number}"
                severity = Severity.MEDIUM
                confidence = Confidence.MEDIUM
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Logging Entire Request/Response Object",
                    description=(
                        "The code logs entire request or response objects. These objects may "
                        "contain sensitive data such as:\n"
                        "- Authentication tokens in headers\n"
                        "- Passwords in request bodies\n"
                        "- Session cookies\n"
                        "- API keys\n"
                        "- Personal information\n\n"
                        "Logging entire objects increases the risk of sensitive data exposure."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Log only specific, non-sensitive fields from requests/responses:\n"
                        "1. Log request method, path, and status code\n"
                        "2. Log user ID or session ID (not tokens)\n"
                        "3. Avoid logging headers, cookies, or request bodies\n"
                        "4. Implement request/response sanitization\n"
                        "5. Use structured logging with explicit fields"
                    ),
                    remediation_code=(
                        "# Bad: Logging entire request\n"
                        "# logger.info(f'Request: {request}')\n\n"
                        "# Good: Log specific non-sensitive fields\n"
                        "logger.info(\n"
                        "    'Request received',\n"
                        "    extra={\n"
                        "        'method': request.method,\n"
                        "        'path': request.url.path,\n"
                        "        'user_id': current_user.id\n"
                        "    }\n"
                        ")"
                    ),
                    cwe_id="CWE-532",
                    owasp_category="A09:2021 - Security Logging and Monitoring Failures",
                    references=[
                        "https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Check for overly verbose logging (debug level in production code)
        debug_log_patterns = [
            (r'logger\.debug\s*\(', 'debug_logging'),
            (r'logging\.DEBUG', 'debug_level'),
        ]
        
        # Only flag if there are many debug statements (more than 5)
        debug_count = 0
        for pattern, pattern_name in debug_log_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name
            )
            debug_count += len(matches)
        
        if debug_count > 5:
            # Check if there's environment-based log level configuration
            has_log_config = bool(re.search(
                r'(LOG_LEVEL|logging\.(?:basicConfig|getLogger))',
                content,
                re.IGNORECASE
            ))
            
            if not has_log_config:
                finding_id = f"infra-verbose-logging-{file_path}"
                severity = Severity.LOW
                confidence = Confidence.LOW
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Overly Verbose Debug Logging",
                    description=(
                        f"The file contains {debug_count} debug-level log statements without "
                        f"apparent log level configuration. Excessive debug logging in production:\n"
                        f"1. Can expose sensitive implementation details\n"
                        f"2. May impact application performance\n"
                        f"3. Can fill disk space with unnecessary logs\n"
                        f"4. Makes it harder to find important log messages\n\n"
                        f"Debug logging should be controlled by environment-specific configuration."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=None,
                    code_snippet=None,
                    remediation=(
                        "Implement environment-based log level configuration:\n"
                        "1. Use INFO or WARNING level in production\n"
                        "2. Use DEBUG level only in development\n"
                        "3. Configure log levels via environment variables\n"
                        "4. Review debug statements for sensitive data\n"
                        "5. Consider using structured logging"
                    ),
                    remediation_code=(
                        "import os\n"
                        "import logging\n\n"
                        "# Configure log level from environment\n"
                        "LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()\n"
                        "logging.basicConfig(\n"
                        "    level=getattr(logging, LOG_LEVEL),\n"
                        "    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'\n"
                        ")\n\n"
                        "logger = logging.getLogger(__name__)"
                    ),
                    cwe_id="CWE-532",
                    owasp_category="A09:2021 - Security Logging and Monitoring Failures",
                    references=[
                        "https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Check for credentials in log statements
        credential_patterns = [
            (r'log(?:ger)?\.(?:debug|info|warning|error|critical)\s*\([^)]*(?:username|user).*(?:password|pwd)[^)]*\)', 'log_credentials'),
            (r'print\s*\([^)]*(?:username|user).*(?:password|pwd)[^)]*\)', 'print_credentials'),
        ]
        
        for pattern, pattern_name in credential_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                finding_id = f"infra-log-credentials-{file_path}-{match.line_number}"
                severity = Severity.CRITICAL
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Credentials Logged in Plain Text",
                    description=(
                        "A log statement appears to include both username and password. "
                        "Logging credentials in plain text is a critical security vulnerability:\n"
                        "1. Credentials are stored unencrypted in log files\n"
                        "2. Anyone with log access can steal credentials\n"
                        "3. Logs may be backed up or sent to third parties\n"
                        "4. Credentials may remain in logs after password changes\n"
                        "5. Violates compliance requirements (PCI-DSS, GDPR, etc.)"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Never log credentials. Instead:\n"
                        "1. Log only the username or user ID\n"
                        "2. Log authentication success/failure without credentials\n"
                        "3. Use audit logs for authentication events\n"
                        "4. Implement log sanitization to remove credentials\n"
                        "5. Review all logging code for credential exposure"
                    ),
                    remediation_code=(
                        "# Bad: Logging credentials\n"
                        "# logger.info(f'Login: {username} / {password}')\n\n"
                        "# Good: Log only username and result\n"
                        "logger.info(f'Login attempt for user: {username}')\n"
                        "# Later:\n"
                        "logger.info(f'Login successful for user: {username}')"
                    ),
                    cwe_id="CWE-532",
                    owasp_category="A09:2021 - Security Logging and Monitoring Failures",
                    references=[
                        "https://owasp.org/www-community/vulnerabilities/Information_exposure_through_query_strings_in_url",
                        "https://cwe.mitre.org/data/definitions/532.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        return findings
