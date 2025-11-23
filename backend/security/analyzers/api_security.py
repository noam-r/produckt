"""API security analyzer for detecting API-specific vulnerabilities."""

import re
from typing import List
from backend.security.analyzers.base import BaseAnalyzer
from backend.security.models.finding import Finding, Severity, Confidence
from backend.security.utils.pattern_matcher import PatternMatcher
from backend.security.utils.ast_parser import ASTParser
from backend.security.utils.severity import SeverityCalculator


class APISecurityAnalyzer(BaseAnalyzer):
    """
    Analyzer for API security vulnerabilities.
    
    Detects issues including:
    - Overly permissive CORS configurations
    - CORS with credentials and wildcard origins
    - Missing rate limiting on endpoints
    - XSS vulnerabilities in HTML responses
    - Missing CSRF protection on state-changing operations
    - Insecure file upload handling
    """
    
    def __init__(self):
        """Initialize API security analyzer."""
        super().__init__()
        self.pattern_matcher = PatternMatcher(context_lines=3)
        self.ast_parser = ASTParser()
        self.severity_calculator = SeverityCalculator()
    
    def get_category(self) -> str:
        """Return the security category."""
        return "api_security"
    
    def analyze(self, file_path: str, content: str) -> List[Finding]:
        """
        Analyze a file for API security vulnerabilities.
        
        Args:
            file_path: Relative path to the file
            content: File content
            
        Returns:
            List of security findings
        """
        findings = []
        
        # Parse AST for structural analysis
        ast_parsed = self.ast_parser.parse(content)
        
        # Check CORS configuration
        findings.extend(self._check_cors_configuration(file_path, content))
        
        # Check rate limiting
        if ast_parsed:
            findings.extend(self._check_rate_limiting(file_path, content))
        
        # Check XSS and CSRF protection
        if ast_parsed:
            findings.extend(self._check_xss_csrf(file_path, content))
        
        return findings
    
    def _check_cors_configuration(self, file_path: str, content: str) -> List[Finding]:
        """Check for insecure CORS configurations."""
        findings = []
        
        # Check for wildcard CORS origins
        wildcard_patterns = [
            (r'allow_origins\s*=\s*\[\s*["\']?\*["\']?\s*\]', 'wildcard_origins'),
            (r'allow_origins\s*=\s*\[\s*["\'][*]["\']?\s*\]', 'wildcard_origins'),
            (r'Access-Control-Allow-Origin\s*["\']:\s*["\'][*]["\']', 'wildcard_header'),
        ]
        
        for pattern, pattern_name in wildcard_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                finding_id = f"api-cors-wildcard-{file_path}-{match.line_number}"
                severity = self.severity_calculator.calculate_severity("cors_misconfiguration")
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Overly Permissive CORS Configuration",
                    description=(
                        f"CORS is configured with wildcard origin (*), allowing any website "
                        f"to make cross-origin requests to this API. This exposes the API to "
                        f"cross-site request forgery and data theft attacks. "
                        f"Found: {match.matched_text}"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Restrict CORS to specific trusted origins. Never use wildcard (*) "
                        "in production. Maintain a whitelist of allowed origins and validate "
                        "against it."
                    ),
                    remediation_code=(
                        "# Specify exact allowed origins\n"
                        "app.add_middleware(\n"
                        "    CORSMiddleware,\n"
                        "    allow_origins=[\n"
                        "        'https://yourdomain.com',\n"
                        "        'https://app.yourdomain.com'\n"
                        "    ],\n"
                        "    allow_credentials=True,\n"
                        "    allow_methods=['GET', 'POST', 'PUT', 'DELETE'],\n"
                        "    allow_headers=['*'],\n"
                        ")"
                    ),
                    cwe_id="CWE-942",
                    owasp_category="A05:2021 - Security Misconfiguration",
                    references=[
                        "https://owasp.org/www-community/attacks/csrf",
                        "https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Check for CORS with credentials and wildcard origins (critical vulnerability)
        cors_credentials_pattern = r'allow_credentials\s*=\s*True'
        credentials_matches = self.pattern_matcher.match_pattern(
            cors_credentials_pattern, content, 'cors_credentials'
        )
        
        wildcard_origin_pattern = r'allow_origins\s*=\s*\[\s*["\']?\*["\']?\s*\]'
        wildcard_matches = self.pattern_matcher.match_pattern(
            wildcard_origin_pattern, content, 'wildcard_check'
        )
        
        if credentials_matches and wildcard_matches:
            # This is a critical vulnerability
            finding_id = f"api-cors-credentials-wildcard-{file_path}"
            severity = Severity.CRITICAL
            confidence = Confidence.HIGH
            
            findings.append(Finding(
                id=finding_id,
                category=self.get_category(),
                title="Critical CORS Misconfiguration: Credentials with Wildcard Origin",
                description=(
                    "CORS is configured with both allow_credentials=True and wildcard "
                    "origin (*). This is a critical security vulnerability that allows "
                    "any website to make authenticated requests to your API, potentially "
                    "stealing user data and performing actions on their behalf. "
                    "Browsers should block this, but it indicates a serious misconfiguration."
                ),
                severity=severity,
                confidence=confidence,
                file_path=file_path,
                line_number=credentials_matches[0].line_number,
                code_snippet=credentials_matches[0].code_snippet,
                remediation=(
                    "NEVER use allow_credentials=True with wildcard origins. Either:\n"
                    "1. Specify exact allowed origins with credentials, OR\n"
                    "2. Use wildcard origins without credentials (not recommended)\n"
                    "The recommended approach is to use specific origins with credentials."
                ),
                remediation_code=(
                    "app.add_middleware(\n"
                    "    CORSMiddleware,\n"
                    "    allow_origins=['https://yourdomain.com'],  # Specific origins only\n"
                    "    allow_credentials=True,\n"
                    "    allow_methods=['GET', 'POST', 'PUT', 'DELETE'],\n"
                    "    allow_headers=['*'],\n"
                    ")"
                ),
                cwe_id="CWE-942",
                owasp_category="A05:2021 - Security Misconfiguration",
                references=[
                    "https://portswigger.net/web-security/cors",
                    "https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS"
                ],
                detected_by=self.get_name()
            ))
        
        # Check for missing CORS restrictions entirely
        has_cors_config = bool(re.search(
            r'(CORSMiddleware|allow_origins|Access-Control-Allow-Origin)',
            content,
            re.IGNORECASE
        ))
        
        has_api_routes = bool(re.search(
            r'@(router|app)\.(get|post|put|delete|patch)',
            content,
            re.IGNORECASE
        ))
        
        if has_api_routes and not has_cors_config:
            finding_id = f"api-no-cors-{file_path}"
            severity = Severity.LOW
            confidence = Confidence.MEDIUM
            
            findings.append(Finding(
                id=finding_id,
                category=self.get_category(),
                title="Missing CORS Configuration",
                description=(
                    "API endpoints detected without CORS configuration. While this may be "
                    "intentional for same-origin APIs, it's important to explicitly configure "
                    "CORS to prevent unintended cross-origin access."
                ),
                severity=severity,
                confidence=confidence,
                file_path=file_path,
                line_number=None,
                code_snippet=None,
                remediation=(
                    "Explicitly configure CORS middleware with appropriate restrictions. "
                    "If the API is only for same-origin use, document this decision. "
                    "If cross-origin access is needed, configure specific allowed origins."
                ),
                remediation_code=(
                    "from fastapi.middleware.cors import CORSMiddleware\n\n"
                    "app.add_middleware(\n"
                    "    CORSMiddleware,\n"
                    "    allow_origins=['https://yourdomain.com'],\n"
                    "    allow_credentials=True,\n"
                    "    allow_methods=['GET', 'POST'],\n"
                    "    allow_headers=['*'],\n"
                    ")"
                ),
                cwe_id="CWE-942",
                owasp_category="A05:2021 - Security Misconfiguration",
                references=[
                    "https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS"
                ],
                detected_by=self.get_name()
            ))
        
        return findings

    def _check_rate_limiting(self, file_path: str, content: str) -> List[Finding]:
        """Check for missing rate limiting on API endpoints."""
        findings = []
        
        # Find all API endpoint definitions
        functions = self.ast_parser.find_functions()
        
        # Check for rate limiting decorators or middleware
        has_rate_limit_middleware = bool(re.search(
            r'(RateLimit|Limiter|rate.*limit|throttle)',
            content,
            re.IGNORECASE
        ))
        
        # Find endpoints without rate limiting
        endpoints_without_rate_limit = []
        
        for func in functions:
            # Check if function is an API endpoint
            is_endpoint = any(
                dec.startswith('router.') or dec.startswith('app.') or 
                'router' in dec or 'app' in dec
                for dec in func.decorators
            )
            
            if not is_endpoint:
                continue
            
            # Check if endpoint has rate limiting decorator
            has_rate_limit = any(
                'limit' in dec.lower() or 'rate' in dec.lower() or 'throttle' in dec.lower()
                for dec in func.decorators
            )
            
            if not has_rate_limit:
                endpoints_without_rate_limit.append(func)
        
        # Report missing rate limiting if no global middleware and endpoints lack decorators
        if endpoints_without_rate_limit and not has_rate_limit_middleware:
            for func in endpoints_without_rate_limit:
                finding_id = f"api-no-rate-limit-{file_path}-{func.line_number}"
                severity = self.severity_calculator.calculate_severity("missing_rate_limiting")
                confidence = Confidence.MEDIUM
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Missing Rate Limiting on API Endpoint",
                    description=(
                        f"API endpoint '{func.name}' does not have rate limiting configured. "
                        f"Without rate limiting, the endpoint is vulnerable to:\n"
                        f"1. Denial of Service (DoS) attacks\n"
                        f"2. Brute force attacks\n"
                        f"3. Resource exhaustion\n"
                        f"4. API abuse and scraping"
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=func.line_number,
                    code_snippet=None,
                    remediation=(
                        "Implement rate limiting using middleware or decorators. "
                        "Recommended approaches:\n"
                        "1. Global rate limiting middleware for all endpoints\n"
                        "2. Per-endpoint rate limiting decorators for sensitive operations\n"
                        "3. Different limits for authenticated vs anonymous users\n"
                        "Typical limits: 100 requests/minute for general endpoints, "
                        "5-10 requests/minute for authentication endpoints."
                    ),
                    remediation_code=(
                        "from slowapi import Limiter\n"
                        "from slowapi.util import get_remote_address\n\n"
                        "limiter = Limiter(key_func=get_remote_address)\n\n"
                        "@router.post('/endpoint')\n"
                        "@limiter.limit('100/minute')  # 100 requests per minute\n"
                        "async def endpoint(request: Request, ...):\n"
                        "    ..."
                    ),
                    cwe_id="CWE-770",
                    owasp_category="A04:2021 - Insecure Design",
                    references=[
                        "https://owasp.org/www-community/controls/Blocking_Brute_Force_Attacks",
                        "https://cheatsheetseries.owasp.org/cheatsheets/Denial_of_Service_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Check for rate limit bypass opportunities
        bypass_patterns = [
            (r'X-Forwarded-For.*without.*validation', 'xff_bypass'),
            (r'get_remote_address.*X-Forwarded-For', 'xff_trust'),
        ]
        
        for pattern, pattern_name in bypass_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                finding_id = f"api-rate-limit-bypass-{file_path}-{match.line_number}"
                severity = Severity.MEDIUM
                confidence = Confidence.LOW
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Potential Rate Limit Bypass via Header Spoofing",
                    description=(
                        "Rate limiting implementation may trust X-Forwarded-For or similar "
                        "headers without validation. Attackers can spoof these headers to "
                        "bypass rate limits by appearing to come from different IP addresses."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Only trust X-Forwarded-For headers when behind a trusted proxy. "
                        "Validate that requests come through your proxy and use the rightmost "
                        "trusted IP address. Consider using multiple rate limiting keys:\n"
                        "1. IP address\n"
                        "2. User ID (for authenticated requests)\n"
                        "3. API key\n"
                        "4. Session ID"
                    ),
                    remediation_code=(
                        "def get_client_ip(request: Request) -> str:\n"
                        "    # Only trust X-Forwarded-For if behind known proxy\n"
                        "    if request.client.host in TRUSTED_PROXIES:\n"
                        "        forwarded = request.headers.get('X-Forwarded-For')\n"
                        "        if forwarded:\n"
                        "            return forwarded.split(',')[0].strip()\n"
                        "    return request.client.host"
                    ),
                    cwe_id="CWE-770",
                    owasp_category="A04:2021 - Insecure Design",
                    references=[
                        "https://owasp.org/www-community/attacks/Denial_of_Service"
                    ],
                    detected_by=self.get_name()
                ))
        
        return findings
    
    def _check_xss_csrf(self, file_path: str, content: str) -> List[Finding]:
        """Check for XSS and CSRF vulnerabilities."""
        findings = []
        
        # Check for HTMLResponse with user data (XSS risk)
        html_response_patterns = [
            (r'HTMLResponse\s*\(.*\{.*\}', 'html_with_data'),
            (r'return.*HTMLResponse.*content\s*=', 'html_return'),
            (r'response_class\s*=\s*HTMLResponse', 'html_response_class'),
        ]
        
        for pattern, pattern_name in html_response_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                # Check if there's any variable interpolation or user input
                has_interpolation = bool(re.search(
                    r'(\{.*\}|%s|%d|\.format|f["\'])',
                    match.code_snippet
                ))
                
                if has_interpolation:
                    finding_id = f"api-xss-html-{file_path}-{match.line_number}"
                    severity = self.severity_calculator.calculate_severity("xss_vulnerability")
                    confidence = Confidence.MEDIUM
                    
                    findings.append(Finding(
                        id=finding_id,
                        category=self.get_category(),
                        title="Potential XSS Vulnerability in HTML Response",
                        description=(
                            "HTMLResponse detected with variable interpolation. If user input "
                            "is included in the HTML without proper escaping, this creates a "
                            "Cross-Site Scripting (XSS) vulnerability. Attackers can inject "
                            "malicious JavaScript that executes in victims' browsers."
                        ),
                        severity=severity,
                        confidence=confidence,
                        file_path=file_path,
                        line_number=match.line_number,
                        code_snippet=match.code_snippet,
                        remediation=(
                            "Always escape user input before including it in HTML responses:\n"
                            "1. Use a templating engine with auto-escaping (Jinja2)\n"
                            "2. Use html.escape() for manual escaping\n"
                            "3. Implement Content Security Policy (CSP) headers\n"
                            "4. Prefer JSON responses over HTML when possible\n"
                            "5. Never use innerHTML or eval() with user data"
                        ),
                        remediation_code=(
                            "from html import escape\n"
                            "from jinja2 import Template\n\n"
                            "# Option 1: Use Jinja2 with auto-escaping\n"
                            "template = Template('<h1>{{ title }}</h1>', autoescape=True)\n"
                            "html = template.render(title=user_input)\n\n"
                            "# Option 2: Manual escaping\n"
                            "safe_input = escape(user_input)\n"
                            "html = f'<h1>{safe_input}</h1>'\n\n"
                            "# Add CSP header\n"
                            "headers = {\n"
                            "    'Content-Security-Policy': \"default-src 'self'\"\n"
                            "}\n"
                            "return HTMLResponse(html, headers=headers)"
                        ),
                        cwe_id="CWE-79",
                        owasp_category="A03:2021 - Injection",
                        references=[
                            "https://owasp.org/www-community/attacks/xss/",
                            "https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html"
                        ],
                        detected_by=self.get_name()
                    ))
        
        # Check for state-changing operations without CSRF protection
        state_changing_methods = ['post', 'put', 'delete', 'patch']
        functions = self.ast_parser.find_functions()
        
        for func in functions:
            # Check if function is a state-changing endpoint
            is_state_changing = any(
                any(method in dec.lower() for method in state_changing_methods)
                for dec in func.decorators
            )
            
            if not is_state_changing:
                continue
            
            # Check for CSRF protection
            has_csrf_protection = bool(re.search(
                r'(csrf|CSRFProtect|verify.*token|check.*token)',
                content,
                re.IGNORECASE
            ))
            
            # Check if endpoint uses cookie-based authentication
            has_cookie_auth = bool(re.search(
                r'(Cookie|session|get_current_user.*cookie)',
                content,
                re.IGNORECASE
            ))
            
            if has_cookie_auth and not has_csrf_protection:
                finding_id = f"api-csrf-{file_path}-{func.line_number}"
                severity = self.severity_calculator.calculate_severity("csrf_vulnerability")
                confidence = Confidence.MEDIUM
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Missing CSRF Protection on State-Changing Operation",
                    description=(
                        f"State-changing endpoint '{func.name}' uses cookie-based authentication "
                        f"without CSRF protection. This allows attackers to trick users into "
                        f"performing unwanted actions by submitting forged requests from "
                        f"malicious websites. The browser automatically includes cookies, "
                        f"making the request appear legitimate."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=func.line_number,
                    code_snippet=None,
                    remediation=(
                        "Implement CSRF protection for cookie-based authentication:\n"
                        "1. Use CSRF tokens (synchronizer token pattern)\n"
                        "2. Verify Origin/Referer headers\n"
                        "3. Use SameSite cookie attribute (Strict or Lax)\n"
                        "4. Consider using token-based auth (JWT) instead of cookies\n"
                        "5. Require custom headers for state-changing operations"
                    ),
                    remediation_code=(
                        "from fastapi_csrf_protect import CsrfProtect\n\n"
                        "@router.post('/update')\n"
                        "async def update_data(\n"
                        "    request: Request,\n"
                        "    csrf_protect: CsrfProtect = Depends()\n"
                        "):\n"
                        "    await csrf_protect.validate_csrf(request)\n"
                        "    # Process request\n"
                        "    ...\n\n"
                        "# Or use SameSite cookies\n"
                        "response.set_cookie(\n"
                        "    key='session',\n"
                        "    value=session_id,\n"
                        "    httponly=True,\n"
                        "    secure=True,\n"
                        "    samesite='strict'  # Prevents CSRF\n"
                        ")"
                    ),
                    cwe_id="CWE-352",
                    owasp_category="A01:2021 - Broken Access Control",
                    references=[
                        "https://owasp.org/www-community/attacks/csrf",
                        "https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        # Check for unescaped user input in responses
        dangerous_patterns = [
            (r'\.innerHTML\s*=.*user', 'innerhtml_user'),
            (r'document\.write\s*\(.*user', 'document_write'),
            (r'eval\s*\(.*user', 'eval_user'),
        ]
        
        for pattern, pattern_name in dangerous_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, pattern_name, flags=re.IGNORECASE
            )
            
            for match in matches:
                finding_id = f"api-xss-dangerous-{file_path}-{match.line_number}"
                severity = Severity.HIGH
                confidence = Confidence.HIGH
                
                findings.append(Finding(
                    id=finding_id,
                    category=self.get_category(),
                    title="Dangerous JavaScript Pattern with User Input",
                    description=(
                        f"Detected use of dangerous JavaScript pattern with user input: "
                        f"{match.matched_text}. This creates a direct XSS vulnerability "
                        f"where attackers can execute arbitrary JavaScript code."
                    ),
                    severity=severity,
                    confidence=confidence,
                    file_path=file_path,
                    line_number=match.line_number,
                    code_snippet=match.code_snippet,
                    remediation=(
                        "Never use innerHTML, document.write, or eval with user input. "
                        "Use safe alternatives:\n"
                        "- Use textContent instead of innerHTML\n"
                        "- Use createElement and appendChild for DOM manipulation\n"
                        "- Use JSON.parse instead of eval\n"
                        "- Sanitize input with DOMPurify if HTML is required"
                    ),
                    remediation_code=(
                        "// Bad: element.innerHTML = userInput;\n"
                        "// Good:\n"
                        "element.textContent = userInput;\n\n"
                        "// Or for HTML content:\n"
                        "import DOMPurify from 'dompurify';\n"
                        "element.innerHTML = DOMPurify.sanitize(userInput);"
                    ),
                    cwe_id="CWE-79",
                    owasp_category="A03:2021 - Injection",
                    references=[
                        "https://owasp.org/www-community/attacks/xss/",
                        "https://cheatsheetseries.owasp.org/cheatsheets/DOM_based_XSS_Prevention_Cheat_Sheet.html"
                    ],
                    detected_by=self.get_name()
                ))
        
        return findings
