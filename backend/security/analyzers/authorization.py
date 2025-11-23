"""Authorization security analyzer for detecting authorization vulnerabilities."""

import re
from typing import List, Optional
from backend.security.analyzers.base import BaseAnalyzer
from backend.security.models.finding import Finding, Severity, Confidence
from backend.security.utils.pattern_matcher import PatternMatcher
from backend.security.utils.ast_parser import ASTParser
from backend.security.utils.severity import SeverityCalculator


class AuthorizationAnalyzer(BaseAnalyzer):
    """
    Analyzer for authorization-related security vulnerabilities.
    
    Detects issues including:
    - Missing authorization decorators on endpoints
    - Missing Depends(get_current_user) or Depends(require_*) patterns
    - Public endpoints that should be protected
    - Missing role validation in endpoints
    - Role bypass vulnerabilities
    - Missing admin endpoint protection
    - Database queries missing organization_id filters
    - Horizontal privilege escalation risks
    - Missing ownership validation in data access
    """
    
    def __init__(self):
        """Initialize authorization analyzer."""
        super().__init__()
        self.pattern_matcher = PatternMatcher(context_lines=3)
        self.ast_parser = ASTParser()
        self.severity_calculator = SeverityCalculator()
    
    def get_category(self) -> str:
        """Return the security category."""
        return "authorization"
    
    def analyze(self, file_path: str, content: str) -> List[Finding]:
        """
        Analyze a file for authorization vulnerabilities.
        
        Args:
            file_path: Relative path to the file
            content: File content
            
        Returns:
            List of security findings
        """
        findings = []
        
        # Skip non-router files for endpoint checks
        is_router_file = 'router' in file_path.lower() or '/routers/' in file_path
        
        if is_router_file:
            # Check for missing authorization on endpoints
            findings.extend(self._check_missing_authorization(file_path, content))
            
            # Check for privilege escalation vulnerabilities
            findings.extend(self._check_privilege_escalation(file_path, content))
        
        # Check multi-tenant isolation in all files (repositories, routers, etc.)
        findings.extend(self._check_multi_tenant_isolation(file_path, content))
        
        return findings
    
    def _check_missing_authorization(self, file_path: str, content: str) -> List[Finding]:
        """Check for API endpoints without authorization decorators."""
        findings = []
        
        # Find all route decorators
        route_patterns = [
            r'@router\.(get|post|put|patch|delete)\s*\([^)]*\)',
            r'@app\.(get|post|put|patch|delete)\s*\([^)]*\)',
        ]
        
        lines = content.split('\n')
        
        for pattern in route_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, 'route_decorator', flags=re.IGNORECASE
            )
            
            for match in matches:
                # Get the function definition following this decorator
                func_line = self._find_function_after_decorator(lines, match.line_number)
                
                if not func_line:
                    continue
                
                # Extract function context (decorator + function + first few lines)
                start_line = max(0, match.line_number - 1)
                end_line = min(len(lines), match.line_number + 15)
                func_context = '\n'.join(lines[start_line:end_line])
                
                # Check if this endpoint has authorization
                has_auth = self._has_authorization_check(func_context)
                
                # Check if this is a public endpoint (login, register, health check)
                is_public_endpoint = self._is_public_endpoint(match.matched_text, func_context)
                
                if not has_auth and not is_public_endpoint:
                    finding_id = f"authz-missing-auth-{file_path}-{match.line_number}"
                    severity = self.severity_calculator.calculate_severity("missing_authorization")
                    confidence = Confidence.HIGH
                    
                    findings.append(Finding(
                        id=finding_id,
                        category=self.get_category(),
                        title="API Endpoint Without Authorization",
                        description=(
                            f"API endpoint detected without authorization checks. "
                            f"The endpoint does not use Depends(get_current_user), "
                            f"Depends(require_admin), or other authorization dependencies. "
                            f"This allows unauthenticated users to access the endpoint.\n\n"
                            f"Endpoint: {match.matched_text}"
                        ),
                        severity=severity,
                        confidence=confidence,
                        file_path=file_path,
                        line_number=match.line_number,
                        code_snippet=match.code_snippet,
                        remediation=(
                            "Add authorization dependency to the endpoint:\n"
                            "1. For authenticated endpoints: Add 'current_user: User = Depends(get_current_user)'\n"
                            "2. For admin endpoints: Add 'current_user: User = Depends(require_admin)'\n"
                            "3. For role-based: Add 'current_user: User = Depends(require_product_manager)'\n"
                            "4. If this is intentionally public, add a comment explaining why"
                        ),
                        remediation_code=(
                            "from backend.auth.dependencies import get_current_user\n"
                            "from backend.models import User\n\n"
                            "@router.get('/protected-endpoint')\n"
                            "def protected_endpoint(\n"
                            "    current_user: User = Depends(get_current_user),  # Add this\n"
                            "    db: Session = Depends(get_db)\n"
                            "):\n"
                            "    # Endpoint logic\n"
                            "    ..."
                        ),
                        cwe_id="CWE-862",
                        owasp_category="A01:2021 - Broken Access Control",
                        references=[
                            "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
                            "https://cwe.mitre.org/data/definitions/862.html"
                        ],
                        detected_by=self.get_name()
                    ))
        
        return findings
    
    def _check_privilege_escalation(self, file_path: str, content: str) -> List[Finding]:
        """Check for privilege escalation vulnerabilities."""
        findings = []
        
        # Check for admin endpoints without proper protection
        admin_endpoint_patterns = [
            r'@router\.(get|post|put|patch|delete)\s*\(["\'].*/(admin|users|roles)',
            r'def\s+(admin|manage|delete_user|create_user|update_user)',
        ]
        
        lines = content.split('\n')
        
        for pattern in admin_endpoint_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, 'admin_endpoint', flags=re.IGNORECASE
            )
            
            for match in matches:
                # Get context around the match
                start_line = max(0, match.line_number - 1)
                end_line = min(len(lines), match.line_number + 15)
                func_context = '\n'.join(lines[start_line:end_line])
                
                # Check if require_admin is used
                has_admin_check = bool(re.search(
                    r'Depends\s*\(\s*require_admin\s*\)',
                    func_context
                ))
                
                # Check if there's any role validation
                has_role_check = bool(re.search(
                    r'(require_admin|require_product_manager|require_role|user\.role\s*==)',
                    func_context,
                    re.IGNORECASE
                ))
                
                if not has_admin_check and 'admin' in match.matched_text.lower():
                    finding_id = f"authz-missing-admin-{file_path}-{match.line_number}"
                    severity = Severity.CRITICAL
                    confidence = Confidence.HIGH
                    
                    findings.append(Finding(
                        id=finding_id,
                        category=self.get_category(),
                        title="Admin Endpoint Without Admin Role Check",
                        description=(
                            f"Admin endpoint detected without require_admin dependency. "
                            f"This allows non-admin users to access administrative functions, "
                            f"leading to vertical privilege escalation.\n\n"
                            f"Endpoint: {match.matched_text}"
                        ),
                        severity=severity,
                        confidence=confidence,
                        file_path=file_path,
                        line_number=match.line_number,
                        code_snippet=match.code_snippet,
                        remediation=(
                            "Add require_admin dependency to admin endpoints:\n"
                            "1. Import: from backend.dependencies.rbac import require_admin\n"
                            "2. Add parameter: current_user: User = Depends(require_admin)\n"
                            "3. This ensures only users with admin role can access the endpoint"
                        ),
                        remediation_code=(
                            "from backend.dependencies.rbac import require_admin\n"
                            "from backend.models import User\n\n"
                            "@router.post('/admin/users')\n"
                            "def create_user(\n"
                            "    current_user: User = Depends(require_admin),  # Add this\n"
                            "    db: Session = Depends(get_db)\n"
                            "):\n"
                            "    # Admin logic\n"
                            "    ..."
                        ),
                        cwe_id="CWE-269",
                        owasp_category="A01:2021 - Broken Access Control",
                        references=[
                            "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
                            "https://cwe.mitre.org/data/definitions/269.html"
                        ],
                        detected_by=self.get_name()
                    ))
                
                # Check for role bypass vulnerabilities
                if has_role_check:
                    # Look for weak role checks that can be bypassed
                    has_weak_check = bool(re.search(
                        r'if\s+.*role.*:',
                        func_context,
                        re.IGNORECASE
                    ))
                    
                    # Check if the role check is not using Depends (less secure)
                    uses_depends = bool(re.search(
                        r'Depends\s*\(\s*require_',
                        func_context
                    ))
                    
                    if has_weak_check and not uses_depends:
                        finding_id = f"authz-weak-role-check-{file_path}-{match.line_number}"
                        severity = Severity.HIGH
                        confidence = Confidence.MEDIUM
                        
                        findings.append(Finding(
                            id=finding_id,
                            category=self.get_category(),
                            title="Weak Role Validation Implementation",
                            description=(
                                "Role validation is implemented using manual checks instead of "
                                "FastAPI dependencies. Manual role checks are error-prone and "
                                "can be bypassed if not implemented correctly in all code paths."
                            ),
                            severity=severity,
                            confidence=confidence,
                            file_path=file_path,
                            line_number=match.line_number,
                            code_snippet=match.code_snippet,
                            remediation=(
                                "Use FastAPI Depends() with role checking functions:\n"
                                "1. Replace manual 'if user.role ==' checks with Depends(require_role)\n"
                                "2. This ensures role checks happen before the endpoint executes\n"
                                "3. Provides consistent error handling and responses"
                            ),
                            remediation_code=(
                                "# Instead of:\n"
                                "def endpoint(user: User = Depends(get_current_user)):\n"
                                "    if user.role != UserRole.ADMIN:\n"
                                "        raise HTTPException(403, 'Forbidden')\n"
                                "    ...\n\n"
                                "# Use:\n"
                                "def endpoint(user: User = Depends(require_admin)):\n"
                                "    ..."
                            ),
                            cwe_id="CWE-285",
                            owasp_category="A01:2021 - Broken Access Control",
                            references=[
                                "https://owasp.org/Top10/A01_2021-Broken_Access_Control/"
                            ],
                            detected_by=self.get_name()
                        ))
        
        return findings
    
    def _check_multi_tenant_isolation(self, file_path: str, content: str) -> List[Finding]:
        """Check for multi-tenant isolation issues."""
        findings = []
        
        # Look for database queries
        query_patterns = [
            r'db\.query\s*\([^)]+\)',
            r'\.filter\s*\([^)]+\)',
            r'\.get\s*\([^)]+\)',
        ]
        
        lines = content.split('\n')
        
        for pattern in query_patterns:
            matches = self.pattern_matcher.match_pattern(
                pattern, content, 'db_query'
            )
            
            for match in matches:
                # Get extended context for the query
                start_line = max(0, match.line_number - 5)
                end_line = min(len(lines), match.line_number + 10)
                query_context = '\n'.join(lines[start_line:end_line])
                
                # Check if this query filters by organization_id
                has_org_filter = bool(re.search(
                    r'organization_id\s*[=!]',
                    query_context
                ))
                
                # Check if this is in a repository or router file
                is_data_access = bool(re.search(
                    r'(repository|router)',
                    file_path.lower()
                ))
                
                # Check if the query is for models that should have org isolation
                # (skip system tables like roles, audit logs in some cases)
                queries_user_data = bool(re.search(
                    r'(User|Initiative|Question|Answer|MRD|Context|Score|Evaluation)',
                    query_context
                ))
                
                # Check if current_user.organization_id is available in context
                has_current_user = bool(re.search(
                    r'current_user',
                    query_context
                ))
                
                if (is_data_access and queries_user_data and 
                    not has_org_filter and has_current_user):
                    finding_id = f"authz-missing-org-filter-{file_path}-{match.line_number}"
                    severity = Severity.CRITICAL
                    confidence = Confidence.MEDIUM
                    
                    findings.append(Finding(
                        id=finding_id,
                        category=self.get_category(),
                        title="Database Query Missing Organization Filter",
                        description=(
                            "Database query detected without organization_id filter. "
                            "In a multi-tenant application, this allows users to access "
                            "data from other organizations, leading to horizontal privilege "
                            "escalation and data leakage.\n\n"
                            f"Query: {match.matched_text}"
                        ),
                        severity=severity,
                        confidence=confidence,
                        file_path=file_path,
                        line_number=match.line_number,
                        code_snippet=match.code_snippet,
                        remediation=(
                            "Add organization_id filter to all queries accessing user data:\n"
                            "1. Always filter by current_user.organization_id\n"
                            "2. Apply filter as early as possible in the query chain\n"
                            "3. Use repository methods that enforce organization isolation\n"
                            "4. Never trust client-provided organization_id values"
                        ),
                        remediation_code=(
                            "# Always include organization_id filter:\n"
                            "initiative = db.query(Initiative).filter(\n"
                            "    Initiative.id == initiative_id,\n"
                            "    Initiative.organization_id == current_user.organization_id  # Add this\n"
                            ").first()\n\n"
                            "# Or use repository methods:\n"
                            "initiative = repo.get_by_id(initiative_id, current_user.organization_id)"
                        ),
                        cwe_id="CWE-639",
                        owasp_category="A01:2021 - Broken Access Control",
                        references=[
                            "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
                            "https://cwe.mitre.org/data/definitions/639.html"
                        ],
                        detected_by=self.get_name()
                    ))
                
                # Check for ownership validation in data access
                # Look for queries that get by ID without checking ownership
                is_get_by_id = bool(re.search(
                    r'\.filter\s*\([^)]*\.id\s*==',
                    match.matched_text
                ))
                
                has_ownership_check = bool(re.search(
                    r'(created_by|user_id|owner_id)\s*==',
                    query_context
                ))
                
                if (is_get_by_id and queries_user_data and 
                    not has_ownership_check and not has_org_filter and
                    has_current_user):
                    finding_id = f"authz-missing-ownership-{file_path}-{match.line_number}"
                    severity = Severity.HIGH
                    confidence = Confidence.LOW
                    
                    findings.append(Finding(
                        id=finding_id,
                        category=self.get_category(),
                        title="Missing Ownership Validation",
                        description=(
                            "Data access by ID without ownership validation. "
                            "Users may be able to access or modify resources they don't own "
                            "by guessing or enumerating IDs. This is a horizontal privilege "
                            "escalation vulnerability."
                        ),
                        severity=severity,
                        confidence=confidence,
                        file_path=file_path,
                        line_number=match.line_number,
                        code_snippet=match.code_snippet,
                        remediation=(
                            "Validate resource ownership before allowing access:\n"
                            "1. Check that resource.created_by == current_user.id\n"
                            "2. Or check resource.organization_id == current_user.organization_id\n"
                            "3. Return 404 (not 403) to avoid information disclosure\n"
                            "4. Apply checks consistently across all CRUD operations"
                        ),
                        remediation_code=(
                            "# Check ownership:\n"
                            "resource = db.query(Resource).filter(\n"
                            "    Resource.id == resource_id,\n"
                            "    Resource.organization_id == current_user.organization_id\n"
                            ").first()\n\n"
                            "if not resource:\n"
                            "    raise HTTPException(404, 'Resource not found')  # Don't reveal existence"
                        ),
                        cwe_id="CWE-639",
                        owasp_category="A01:2021 - Broken Access Control",
                        references=[
                            "https://owasp.org/Top10/A01_2021-Broken_Access_Control/",
                            "https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html"
                        ],
                        detected_by=self.get_name()
                    ))
        
        return findings
    
    def _find_function_after_decorator(self, lines: List[str], decorator_line: int) -> Optional[int]:
        """Find the function definition line after a decorator."""
        for i in range(decorator_line, min(len(lines), decorator_line + 10)):
            if lines[i].strip().startswith('def ') or lines[i].strip().startswith('async def '):
                return i
        return None
    
    def _has_authorization_check(self, func_context: str) -> bool:
        """Check if function context has authorization checks."""
        auth_patterns = [
            r'Depends\s*\(\s*get_current_user\s*\)',
            r'Depends\s*\(\s*require_admin\s*\)',
            r'Depends\s*\(\s*require_product_manager\s*\)',
            r'Depends\s*\(\s*require_role\s*\(',
            r'current_user\s*:\s*User\s*=\s*Depends',
        ]
        
        for pattern in auth_patterns:
            if re.search(pattern, func_context):
                return True
        
        return False
    
    def _is_public_endpoint(self, route_decorator: str, func_context: str) -> bool:
        """Check if this is an intentionally public endpoint."""
        public_patterns = [
            r'/(login|register|signin|signup|auth)',
            r'/(health|ping|status|version)',
            r'/(docs|openapi|redoc)',
            r'/public/',
        ]
        
        for pattern in public_patterns:
            if re.search(pattern, route_decorator, re.IGNORECASE):
                return True
        
        # Check for explicit public comment
        if re.search(r'#.*public', func_context, re.IGNORECASE):
            return True
        
        return False
