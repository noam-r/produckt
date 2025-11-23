"""AST parsing utility for Python code analysis."""

import ast
from typing import List, Optional, Set, Dict, Any, Callable
from dataclasses import dataclass, field


@dataclass
class FunctionInfo:
    """Information about a function definition."""
    
    name: str
    line_number: int
    decorators: List[str]
    args: List[str]
    returns: Optional[str]
    is_async: bool
    docstring: Optional[str]


@dataclass
class ClassInfo:
    """Information about a class definition."""
    
    name: str
    line_number: int
    decorators: List[str]
    bases: List[str]
    methods: List[FunctionInfo]
    docstring: Optional[str]


@dataclass
class ImportInfo:
    """Information about an import statement."""
    
    module: str
    names: List[str]
    line_number: int
    is_from_import: bool


@dataclass
class CallInfo:
    """Information about a function call."""
    
    function_name: str
    line_number: int
    args: List[str]
    kwargs: Dict[str, str]


class ASTParser:
    """Utility for parsing and analyzing Python AST."""
    
    def __init__(self):
        """Initialize AST parser."""
        self.tree: Optional[ast.AST] = None
        self.source_lines: List[str] = []
    
    def parse(self, content: str) -> bool:
        """
        Parse Python code into AST.
        
        Args:
            content: Python source code
            
        Returns:
            True if parsing succeeded, False otherwise
        """
        try:
            self.tree = ast.parse(content)
            self.source_lines = content.split('\n')
            return True
        except SyntaxError:
            self.tree = None
            self.source_lines = []
            return False
    
    def find_functions(self) -> List[FunctionInfo]:
        """
        Find all function definitions in the AST.
        
        Returns:
            List of FunctionInfo objects
        """
        if not self.tree:
            return []
        
        functions = []
        
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_info = self._extract_function_info(node)
                functions.append(func_info)
        
        return functions
    
    def find_classes(self) -> List[ClassInfo]:
        """
        Find all class definitions in the AST.
        
        Returns:
            List of ClassInfo objects
        """
        if not self.tree:
            return []
        
        classes = []
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef):
                class_info = self._extract_class_info(node)
                classes.append(class_info)
        
        return classes
    
    def find_imports(self) -> List[ImportInfo]:
        """
        Find all import statements in the AST.
        
        Returns:
            List of ImportInfo objects
        """
        if not self.tree:
            return []
        
        imports = []
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    import_info = ImportInfo(
                        module=alias.name,
                        names=[alias.asname or alias.name],
                        line_number=node.lineno,
                        is_from_import=False
                    )
                    imports.append(import_info)
            
            elif isinstance(node, ast.ImportFrom):
                names = [alias.asname or alias.name for alias in node.names]
                import_info = ImportInfo(
                    module=node.module or "",
                    names=names,
                    line_number=node.lineno,
                    is_from_import=True
                )
                imports.append(import_info)
        
        return imports
    
    def find_function_calls(self, function_name: Optional[str] = None) -> List[CallInfo]:
        """
        Find function calls in the AST.
        
        Args:
            function_name: Optional filter for specific function name
            
        Returns:
            List of CallInfo objects
        """
        if not self.tree:
            return []
        
        calls = []
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node.func)
                
                if function_name is None or call_name == function_name:
                    call_info = self._extract_call_info(node, call_name)
                    calls.append(call_info)
        
        return calls
    
    def find_decorators(self, decorator_name: str) -> List[FunctionInfo]:
        """
        Find functions with a specific decorator.
        
        Args:
            decorator_name: Name of decorator to search for
            
        Returns:
            List of FunctionInfo objects with the decorator
        """
        functions = self.find_functions()
        return [f for f in functions if decorator_name in f.decorators]
    
    def find_functions_without_decorator(
        self,
        required_decorators: List[str],
        exclude_private: bool = True
    ) -> List[FunctionInfo]:
        """
        Find functions missing required decorators.
        
        Args:
            required_decorators: List of decorator names (any match is OK)
            exclude_private: Whether to exclude private functions (starting with _)
            
        Returns:
            List of FunctionInfo objects missing decorators
        """
        functions = self.find_functions()
        missing = []
        
        for func in functions:
            if exclude_private and func.name.startswith('_'):
                continue
            
            has_required = any(dec in func.decorators for dec in required_decorators)
            if not has_required:
                missing.append(func)
        
        return missing
    
    def find_string_concatenation_in_calls(
        self,
        function_names: List[str]
    ) -> List[CallInfo]:
        """
        Find function calls that use string concatenation in arguments.
        Useful for detecting SQL injection vulnerabilities.
        
        Args:
            function_names: List of function names to check
            
        Returns:
            List of CallInfo objects with string concatenation
        """
        if not self.tree:
            return []
        
        vulnerable_calls = []
        
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                call_name = self._get_call_name(node.func)
                
                if call_name in function_names:
                    # Check if any argument uses string concatenation or f-strings
                    if self._has_string_concatenation(node):
                        call_info = self._extract_call_info(node, call_name)
                        vulnerable_calls.append(call_info)
        
        return vulnerable_calls
    
    def visit_nodes(self, visitor: Callable[[ast.AST], None]):
        """
        Visit all nodes in the AST with a custom visitor function.
        
        Args:
            visitor: Function that takes an AST node
        """
        if not self.tree:
            return
        
        for node in ast.walk(self.tree):
            visitor(node)
    
    def _extract_function_info(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> FunctionInfo:
        """Extract information from a function definition node."""
        decorators = [self._get_decorator_name(dec) for dec in node.decorator_list]
        args = [arg.arg for arg in node.args.args]
        
        returns = None
        if node.returns:
            returns = ast.unparse(node.returns)
        
        docstring = ast.get_docstring(node)
        
        return FunctionInfo(
            name=node.name,
            line_number=node.lineno,
            decorators=decorators,
            args=args,
            returns=returns,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            docstring=docstring
        )
    
    def _extract_class_info(self, node: ast.ClassDef) -> ClassInfo:
        """Extract information from a class definition node."""
        decorators = [self._get_decorator_name(dec) for dec in node.decorator_list]
        bases = [ast.unparse(base) for base in node.bases]
        
        methods = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                methods.append(self._extract_function_info(item))
        
        docstring = ast.get_docstring(node)
        
        return ClassInfo(
            name=node.name,
            line_number=node.lineno,
            decorators=decorators,
            bases=bases,
            methods=methods,
            docstring=docstring
        )
    
    def _extract_call_info(self, node: ast.Call, call_name: str) -> CallInfo:
        """Extract information from a function call node."""
        args = []
        for arg in node.args:
            try:
                args.append(ast.unparse(arg))
            except:
                args.append("<unparseable>")
        
        kwargs = {}
        for keyword in node.keywords:
            try:
                kwargs[keyword.arg or "**"] = ast.unparse(keyword.value)
            except:
                kwargs[keyword.arg or "**"] = "<unparseable>"
        
        return CallInfo(
            function_name=call_name,
            line_number=node.lineno,
            args=args,
            kwargs=kwargs
        )
    
    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """Get the name of a decorator."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            return self._get_call_name(decorator.func)
        elif isinstance(decorator, ast.Attribute):
            return ast.unparse(decorator)
        else:
            return ast.unparse(decorator)
    
    def _get_call_name(self, func: ast.expr) -> str:
        """Get the name of a function being called."""
        if isinstance(func, ast.Name):
            return func.id
        elif isinstance(func, ast.Attribute):
            return ast.unparse(func)
        else:
            try:
                return ast.unparse(func)
            except:
                return "<unknown>"
    
    def _has_string_concatenation(self, call_node: ast.Call) -> bool:
        """Check if a call uses string concatenation in arguments."""
        for arg in call_node.args:
            if self._is_string_concat(arg):
                return True
        
        for keyword in call_node.keywords:
            if self._is_string_concat(keyword.value):
                return True
        
        return False
    
    def _is_string_concat(self, node: ast.expr) -> bool:
        """Check if a node represents string concatenation."""
        # Check for BinOp with Add (string + string)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return True
        
        # Check for JoinedStr (f-strings)
        if isinstance(node, ast.JoinedStr):
            return True
        
        # Check for % formatting
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            return True
        
        # Check for .format() calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr == "format":
                    return True
        
        return False


class SecurityVisitor(ast.NodeVisitor):
    """Custom AST visitor for security-specific patterns."""
    
    def __init__(self):
        """Initialize security visitor."""
        self.findings: List[Dict[str, Any]] = []
    
    def visit_Call(self, node: ast.Call):
        """Visit function call nodes."""
        # Override in subclasses to detect specific patterns
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition nodes."""
        # Override in subclasses to detect specific patterns
        self.generic_visit(node)
    
    def visit_Assign(self, node: ast.Assign):
        """Visit assignment nodes."""
        # Override in subclasses to detect specific patterns
        self.generic_visit(node)
