"""Pattern matching utility for regex-based vulnerability detection."""

import re
from typing import List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class PatternMatch:
    """Represents a pattern match with context."""
    
    pattern_name: str
    matched_text: str
    line_number: int
    column_start: int
    column_end: int
    code_snippet: str
    context_before: List[str]
    context_after: List[str]


class PatternMatcher:
    """Utility for regex-based pattern matching with context extraction."""
    
    def __init__(self, context_lines: int = 2):
        """
        Initialize pattern matcher.
        
        Args:
            context_lines: Number of lines to include before/after match
        """
        self.context_lines = context_lines
    
    def match_pattern(
        self,
        pattern: str,
        content: str,
        pattern_name: str,
        flags: int = 0
    ) -> List[PatternMatch]:
        """
        Match a regex pattern against content and extract context.
        
        Args:
            pattern: Regex pattern to match
            content: Content to search
            pattern_name: Name/description of the pattern
            flags: Regex flags (e.g., re.IGNORECASE)
            
        Returns:
            List of PatternMatch objects with context
        """
        matches = []
        lines = content.split('\n')
        
        # Compile pattern
        try:
            compiled_pattern = re.compile(pattern, flags)
        except re.error as e:
            # Invalid regex pattern
            return []
        
        # Search line by line to track line numbers
        for line_idx, line in enumerate(lines):
            for match in compiled_pattern.finditer(line):
                line_number = line_idx + 1  # 1-indexed
                
                # Extract context
                context_before = self._get_context_before(lines, line_idx)
                context_after = self._get_context_after(lines, line_idx)
                
                # Create code snippet with context
                snippet_lines = context_before + [line] + context_after
                code_snippet = '\n'.join(snippet_lines)
                
                pattern_match = PatternMatch(
                    pattern_name=pattern_name,
                    matched_text=match.group(0),
                    line_number=line_number,
                    column_start=match.start(),
                    column_end=match.end(),
                    code_snippet=code_snippet,
                    context_before=context_before,
                    context_after=context_after
                )
                
                matches.append(pattern_match)
        
        return matches
    
    def match_multiline_pattern(
        self,
        pattern: str,
        content: str,
        pattern_name: str,
        flags: int = 0
    ) -> List[PatternMatch]:
        """
        Match a regex pattern that may span multiple lines.
        
        Args:
            pattern: Regex pattern to match
            content: Content to search
            pattern_name: Name/description of the pattern
            flags: Regex flags (e.g., re.MULTILINE, re.DOTALL)
            
        Returns:
            List of PatternMatch objects with context
        """
        matches = []
        lines = content.split('\n')
        
        # Compile pattern
        try:
            compiled_pattern = re.compile(pattern, flags)
        except re.error:
            return []
        
        # Search entire content
        for match in compiled_pattern.finditer(content):
            # Find line number of match start
            line_number = content[:match.start()].count('\n') + 1
            line_idx = line_number - 1
            
            # Calculate column position
            line_start_pos = content.rfind('\n', 0, match.start()) + 1
            column_start = match.start() - line_start_pos
            
            # Extract context
            context_before = self._get_context_before(lines, line_idx)
            context_after = self._get_context_after(lines, line_idx)
            
            # Create code snippet
            matched_text = match.group(0)
            snippet_lines = context_before + [lines[line_idx]] + context_after
            code_snippet = '\n'.join(snippet_lines)
            
            pattern_match = PatternMatch(
                pattern_name=pattern_name,
                matched_text=matched_text,
                line_number=line_number,
                column_start=column_start,
                column_end=column_start + len(matched_text),
                code_snippet=code_snippet,
                context_before=context_before,
                context_after=context_after
            )
            
            matches.append(pattern_match)
        
        return matches
    
    def match_multiple_patterns(
        self,
        patterns: List[Tuple[str, str]],
        content: str,
        flags: int = 0
    ) -> List[PatternMatch]:
        """
        Match multiple patterns against content.
        
        Args:
            patterns: List of (pattern, pattern_name) tuples
            content: Content to search
            flags: Regex flags to apply to all patterns
            
        Returns:
            Combined list of all matches
        """
        all_matches = []
        
        for pattern, pattern_name in patterns:
            matches = self.match_pattern(pattern, content, pattern_name, flags)
            all_matches.extend(matches)
        
        # Sort by line number
        all_matches.sort(key=lambda m: m.line_number)
        
        return all_matches
    
    def _get_context_before(self, lines: List[str], line_idx: int) -> List[str]:
        """Get context lines before the match."""
        start_idx = max(0, line_idx - self.context_lines)
        return lines[start_idx:line_idx]
    
    def _get_context_after(self, lines: List[str], line_idx: int) -> List[str]:
        """Get context lines after the match."""
        end_idx = min(len(lines), line_idx + self.context_lines + 1)
        return lines[line_idx + 1:end_idx]
    
    def extract_code_snippet(
        self,
        content: str,
        line_number: int,
        context_lines: Optional[int] = None
    ) -> str:
        """
        Extract a code snippet around a specific line number.
        
        Args:
            content: Full file content
            line_number: Line number (1-indexed)
            context_lines: Override default context lines
            
        Returns:
            Code snippet with context
        """
        lines = content.split('\n')
        line_idx = line_number - 1
        
        if line_idx < 0 or line_idx >= len(lines):
            return ""
        
        ctx_lines = context_lines if context_lines is not None else self.context_lines
        
        start_idx = max(0, line_idx - ctx_lines)
        end_idx = min(len(lines), line_idx + ctx_lines + 1)
        
        snippet_lines = lines[start_idx:end_idx]
        return '\n'.join(snippet_lines)
