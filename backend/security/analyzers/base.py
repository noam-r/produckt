"""Base analyzer abstract class for security vulnerability detection."""

from abc import ABC, abstractmethod
from typing import List
from backend.security.models.finding import Finding


class BaseAnalyzer(ABC):
    """
    Abstract base class for all security analyzers.
    
    Each analyzer is responsible for detecting specific types of security
    vulnerabilities in the codebase. Analyzers should be stateless and
    thread-safe to allow parallel execution.
    """
    
    def __init__(self):
        """Initialize the analyzer."""
        pass
    
    @abstractmethod
    def analyze(self, file_path: str, content: str) -> List[Finding]:
        """
        Analyze a single file and return security findings.
        
        Args:
            file_path: Relative path to the file being analyzed
            content: Full content of the file as a string
            
        Returns:
            List of Finding objects representing detected vulnerabilities
        """
        pass
    
    @abstractmethod
    def get_category(self) -> str:
        """
        Return the security category this analyzer covers.
        
        Returns:
            Category name (e.g., "authentication", "authorization", "data_protection")
        """
        pass
    
    def should_analyze_file(self, file_path: str) -> bool:
        """
        Determine if this file should be analyzed by this analyzer.
        
        By default, only Python files are analyzed. Subclasses can override
        this method to implement custom file filtering logic.
        
        Args:
            file_path: Relative path to the file
            
        Returns:
            True if the file should be analyzed, False otherwise
        """
        return file_path.endswith('.py')
    
    def get_name(self) -> str:
        """
        Return the name of this analyzer.
        
        Returns:
            Analyzer name (defaults to class name)
        """
        return self.__class__.__name__
