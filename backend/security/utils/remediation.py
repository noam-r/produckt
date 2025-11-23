"""Remediation guidance utilities for security findings."""

from typing import Dict, Optional, List


class RemediationGuide:
    """
    Provides comprehensive remediation guidance for security vulnerabilities.
    
    This class centralizes remediation information including descriptions,
    fix steps, code examples, and references to security standards.
    """
    
    # Remediation templates for common vulnerability types
    REMEDIATION_TEMPLATES = {
        "weak_password_hashing": {
            "description": (
                "Weak password hashing algorithms like MD5, SHA1, and SHA256 are not "
                "suitable for password storage. They are too fast and vulnerable to "
                "brute force attacks. Modern password hashing should use algorithms "
                "specifically designed for this purpose with built-in salting and "
                "configurable work factors."
            ),
            "remediation": (
                "Replace weak hashing algorithms with bcrypt, scrypt, or Argon2. "
                "These algorithms are specifically designed for password storage with "
                "built-in salting and configurable work factors. Use at least 12 rounds "
                "for bcrypt."
            ),
            "code_example": (
                "import bcrypt\n\n"
                "def hash_password(password: str) -> str:\n"
                "    password_bytes = password.encode('utf-8')\n"
                "    salt = bcrypt.gensalt(rounds=12)\n"
                "    hashed = bcrypt.hashpw(password_bytes, salt)\n"
                "    return hashed.decode('utf-8')\n\n"
                "def verify_password(password: str, hashed: str) -> bool:\n"
                "    password_bytes = password.encode('utf-8')\n"
                "    hashed_bytes = hashed.encode('utf-8')\n"
                "    return bcrypt.checkpw(password_bytes, hashed_bytes)"
            ),
            "cwe_id": "CWE-916",
            "owasp_category": "A02:2021 - Cryptographic Failures",
            "references": [
                "https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html",
                "https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/09-Testing_for_Weak_Cryptography/04-Testing_for_Weak_Encryption",
            ],
        },
        "insecure_session_storage": {
            "description": (
                "In-memory session storage without persistence can lead to session loss "
                "on server restart and doesn't scale across multiple server instances. "
                "It also makes session management vulnerable to memory-based attacks."
            ),
            "remediation": (
                "Use a persistent session store like Redis or a database. This ensures "
                "sessions survive server restarts and can be shared across multiple "
                "server instances. Implement proper session expiration and cleanup."
            ),
            "code_example": (
                "from redis import Redis\n"
                "from datetime import timedelta\n\n"
                "redis_client = Redis(host='localhost', port=6379, db=0)\n\n"
                "def store_session(session_id: str, user_id: int, ttl: int = 3600):\n"
                "    redis_client.setex(\n"
                "        f'session:{session_id}',\n"
                "        timedelta(seconds=ttl),\n"
                "        str(user_id)\n"
                "    )"
            ),
            "cwe_id": "CWE-613",
            "owasp_category": "A07:2021 - Identification and Authentication Failures",
            "references": [
                "https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html",
            ],
        },
        "missing_authorization": {
            "description": (
                "API endpoints without authorization checks allow any authenticated user "
                "to access resources they shouldn't have access to. This can lead to "
                "unauthorized data access and privilege escalation."
            ),
            "remediation": (
                "Add authorization checks to all API endpoints using dependency injection. "
                "Use Depends(get_current_user) for user authentication and Depends(require_role) "
                "for role-based access control. Verify ownership for user-specific resources."
            ),
            "code_example": (
                "from fastapi import Depends, HTTPException\n"
                "from backend.auth.dependencies import get_current_user, require_admin\n\n"
                "@router.get('/users/{user_id}')\n"
                "async def get_user(\n"
                "    user_id: int,\n"
                "    current_user: User = Depends(get_current_user)\n"
                "):\n"
                "    # Verify ownership\n"
                "    if current_user.id != user_id and not current_user.is_admin:\n"
                "        raise HTTPException(status_code=403, detail='Access denied')\n"
                "    return await get_user_by_id(user_id)"
            ),
            "cwe_id": "CWE-862",
            "owasp_category": "A01:2021 - Broken Access Control",
            "references": [
                "https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html",
            ],
        },
        "sql_injection": {
            "description": (
                "SQL injection vulnerabilities occur when user input is directly concatenated "
                "into SQL queries. Attackers can manipulate queries to access, modify, or "
                "delete unauthorized data."
            ),
            "remediation": (
                "Always use parameterized queries or ORM methods. Never concatenate user "
                "input directly into SQL queries. Use SQLAlchemy's query builder or "
                "parameterized raw SQL with bound parameters."
            ),
            "code_example": (
                "# Bad - SQL Injection vulnerable\n"
                "# query = f\"SELECT * FROM users WHERE username = '{username}'\"\n\n"
                "# Good - Using SQLAlchemy ORM\n"
                "from sqlalchemy import select\n\n"
                "stmt = select(User).where(User.username == username)\n"
                "result = await session.execute(stmt)\n\n"
                "# Good - Using parameterized query\n"
                "stmt = text('SELECT * FROM users WHERE username = :username')\n"
                "result = await session.execute(stmt, {'username': username})"
            ),
            "cwe_id": "CWE-89",
            "owasp_category": "A03:2021 - Injection",
            "references": [
                "https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html",
            ],
        },
        "sensitive_data_exposure": {
            "description": (
                "Exposing sensitive data like passwords, API keys, or tokens in API responses "
                "or logs can lead to credential theft and unauthorized access."
            ),
            "remediation": (
                "Never include sensitive fields in API response models. Use Pydantic models "
                "with explicit field inclusion. Exclude sensitive fields from logs and error "
                "messages. Use field-level encryption for sensitive data at rest."
            ),
            "code_example": (
                "from pydantic import BaseModel, Field\n\n"
                "class UserResponse(BaseModel):\n"
                "    id: int\n"
                "    username: str\n"
                "    email: str\n"
                "    # Never include password_hash, api_key, etc.\n"
                "    \n"
                "    class Config:\n"
                "        from_attributes = True\n"
                "        # Explicitly exclude sensitive fields\n"
                "        exclude = {'password_hash', 'api_key', 'secret_token'}"
            ),
            "cwe_id": "CWE-200",
            "owasp_category": "A02:2021 - Cryptographic Failures",
            "references": [
                "https://cheatsheetseries.owasp.org/cheatsheets/Sensitive_Data_Exposure_Prevention_Cheat_Sheet.html",
            ],
        },
        "cors_misconfiguration": {
            "description": (
                "Overly permissive CORS configuration (allow_origins=['*']) allows any "
                "website to make requests to your API, potentially exposing sensitive "
                "data to malicious sites."
            ),
            "remediation": (
                "Configure CORS with specific allowed origins. Never use wildcard (*) "
                "with credentials. List only trusted domains that need access to your API."
            ),
            "code_example": (
                "from fastapi.middleware.cors import CORSMiddleware\n\n"
                "app.add_middleware(\n"
                "    CORSMiddleware,\n"
                "    allow_origins=[\n"
                "        'https://yourdomain.com',\n"
                "        'https://app.yourdomain.com',\n"
                "    ],\n"
                "    allow_credentials=True,\n"
                "    allow_methods=['GET', 'POST', 'PUT', 'DELETE'],\n"
                "    allow_headers=['*'],\n"
                ")"
            ),
            "cwe_id": "CWE-942",
            "owasp_category": "A05:2021 - Security Misconfiguration",
            "references": [
                "https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html",
            ],
        },
        "hardcoded_secrets": {
            "description": (
                "Hardcoded secrets in source code can be discovered by anyone with access "
                "to the repository, including through version control history. This leads "
                "to credential exposure and unauthorized access."
            ),
            "remediation": (
                "Store all secrets in environment variables or a secure secrets management "
                "system. Use .env files for local development (never commit them) and "
                "proper secrets management in production (AWS Secrets Manager, HashiCorp Vault, etc.)."
            ),
            "code_example": (
                "import os\n"
                "from dotenv import load_dotenv\n\n"
                "load_dotenv()\n\n"
                "# Bad - Hardcoded secret\n"
                "# API_KEY = 'sk-1234567890abcdef'\n\n"
                "# Good - Load from environment\n"
                "API_KEY = os.getenv('API_KEY')\n"
                "if not API_KEY:\n"
                "    raise ValueError('API_KEY environment variable not set')"
            ),
            "cwe_id": "CWE-798",
            "owasp_category": "A05:2021 - Security Misconfiguration",
            "references": [
                "https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html",
            ],
        },
    }
    
    @classmethod
    def get_remediation(
        cls,
        vulnerability_type: str,
        custom_description: Optional[str] = None,
        custom_remediation: Optional[str] = None,
    ) -> Dict[str, any]:
        """
        Get remediation guidance for a vulnerability type.
        
        Args:
            vulnerability_type: Type of vulnerability
            custom_description: Optional custom description to override template
            custom_remediation: Optional custom remediation to override template
            
        Returns:
            Dictionary with remediation information
        """
        template = cls.REMEDIATION_TEMPLATES.get(vulnerability_type, {})
        
        return {
            "description": custom_description or template.get("description", ""),
            "remediation": custom_remediation or template.get("remediation", ""),
            "code_example": template.get("code_example", ""),
            "cwe_id": template.get("cwe_id"),
            "owasp_category": template.get("owasp_category"),
            "references": template.get("references", []),
        }
    
    @classmethod
    def get_all_vulnerability_types(cls) -> List[str]:
        """Get list of all supported vulnerability types."""
        return list(cls.REMEDIATION_TEMPLATES.keys())
    
    @classmethod
    def add_custom_remediation(
        cls,
        vulnerability_type: str,
        description: str,
        remediation: str,
        code_example: Optional[str] = None,
        cwe_id: Optional[str] = None,
        owasp_category: Optional[str] = None,
        references: Optional[List[str]] = None,
    ) -> None:
        """
        Add or update a custom remediation template.
        
        Args:
            vulnerability_type: Unique identifier for the vulnerability type
            description: Detailed description of the vulnerability
            remediation: Steps to remediate the vulnerability
            code_example: Optional code example showing the fix
            cwe_id: Optional CWE identifier
            owasp_category: Optional OWASP Top 10 category
            references: Optional list of reference URLs
        """
        cls.REMEDIATION_TEMPLATES[vulnerability_type] = {
            "description": description,
            "remediation": remediation,
            "code_example": code_example or "",
            "cwe_id": cwe_id,
            "owasp_category": owasp_category,
            "references": references or [],
        }
