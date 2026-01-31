"""
Code Analyzer - Static code analysis and metrics.
"""

import ast
import re
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path


@dataclass
class CodeMetrics:
    """Metrics extracted from code analysis."""
    lines_of_code: int = 0
    blank_lines: int = 0
    comment_lines: int = 0
    functions: list[str] = field(default_factory=list)
    classes: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    complexity: int = 0
    issues: list[str] = field(default_factory=list)


@dataclass
class FunctionInfo:
    """Information about a function."""
    name: str
    args: list[str]
    returns: Optional[str]
    docstring: Optional[str]
    line_number: int
    complexity: int


@dataclass
class ClassInfo:
    """Information about a class."""
    name: str
    bases: list[str]
    methods: list[str]
    docstring: Optional[str]
    line_number: int


class CodeAnalyzer:
    """Analyzes code for metrics, structure, and potential issues."""

    SUPPORTED_LANGUAGES = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".jsx": "javascript",
        ".tsx": "typescript",
        ".java": "java",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".hpp": "cpp",
    }

    def __init__(self):
        self._cache: dict[str, CodeMetrics] = {}

    def analyze_code(self, code: str, language: str = "python") -> CodeMetrics:
        """
        Analyze code and return metrics.

        Args:
            code: Source code to analyze
            language: Programming language

        Returns:
            CodeMetrics object with analysis results
        """
        metrics = CodeMetrics()
        lines = code.split("\n")

        metrics.lines_of_code = len([l for l in lines if l.strip()])
        metrics.blank_lines = len([l for l in lines if not l.strip()])

        if language == "python":
            metrics = self._analyze_python(code, metrics)
        else:
            metrics = self._analyze_generic(code, metrics, language)

        return metrics

    def analyze_file(self, file_path: str) -> CodeMetrics:
        """Analyze a file and return metrics."""
        path = Path(file_path)

        if not path.exists():
            metrics = CodeMetrics()
            metrics.issues.append(f"File not found: {file_path}")
            return metrics

        suffix = path.suffix.lower()
        language = self.SUPPORTED_LANGUAGES.get(suffix, "unknown")

        code = path.read_text(encoding="utf-8")
        return self.analyze_code(code, language)

    def _analyze_python(self, code: str, metrics: CodeMetrics) -> CodeMetrics:
        """Detailed analysis for Python code."""
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            metrics.issues.append(f"Syntax error: {e}")
            return metrics

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    metrics.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    metrics.imports.append(f"{module}.{alias.name}")
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                metrics.functions.append(node.name)
                metrics.complexity += self._calculate_complexity(node)
            elif isinstance(node, ast.ClassDef):
                metrics.classes.append(node.name)

        # Count comment lines
        for line in code.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                metrics.comment_lines += 1

        # Check for common issues
        metrics.issues.extend(self._check_python_issues(tree, code))

        return metrics

    def _analyze_generic(self, code: str, metrics: CodeMetrics, language: str) -> CodeMetrics:
        """Generic analysis for non-Python languages."""
        lines = code.split("\n")

        # Count comments based on language
        comment_patterns = {
            "javascript": (r"//.*$", r"/\*[\s\S]*?\*/"),
            "typescript": (r"//.*$", r"/\*[\s\S]*?\*/"),
            "java": (r"//.*$", r"/\*[\s\S]*?\*/"),
            "go": (r"//.*$", r"/\*[\s\S]*?\*/"),
            "rust": (r"//.*$", r"/\*[\s\S]*?\*/"),
            "c": (r"//.*$", r"/\*[\s\S]*?\*/"),
            "cpp": (r"//.*$", r"/\*[\s\S]*?\*/"),
            "ruby": (r"#.*$", r"=begin[\s\S]*?=end"),
            "php": (r"//.*$|#.*$", r"/\*[\s\S]*?\*/"),
        }

        patterns = comment_patterns.get(language, (r"#.*$", r""))

        for line in lines:
            if re.search(patterns[0], line):
                metrics.comment_lines += 1

        # Find function/method definitions
        func_patterns = {
            "javascript": r"(?:function\s+(\w+)|(\w+)\s*[=:]\s*(?:async\s+)?function|\b(\w+)\s*\([^)]*\)\s*{)",
            "typescript": r"(?:function\s+(\w+)|(\w+)\s*[=:]\s*(?:async\s+)?function|\b(\w+)\s*\([^)]*\)\s*[:{])",
            "java": r"(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(",
            "go": r"func\s+(?:\([^)]+\)\s+)?(\w+)\s*\(",
            "rust": r"fn\s+(\w+)\s*[<(]",
            "ruby": r"def\s+(\w+)",
            "php": r"function\s+(\w+)\s*\(",
        }

        if language in func_patterns:
            for match in re.finditer(func_patterns[language], code):
                name = next((g for g in match.groups() if g), None)
                if name:
                    metrics.functions.append(name)

        # Find class definitions
        class_patterns = {
            "javascript": r"class\s+(\w+)",
            "typescript": r"class\s+(\w+)",
            "java": r"class\s+(\w+)",
            "rust": r"(?:struct|enum|trait)\s+(\w+)",
            "ruby": r"class\s+(\w+)",
            "php": r"class\s+(\w+)",
        }

        if language in class_patterns:
            for match in re.finditer(class_patterns[language], code):
                metrics.classes.append(match.group(1))

        return metrics

    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1

        for child in ast.walk(node):
            if isinstance(child, ast.If | ast.While | ast.For | ast.ExceptHandler):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.comprehension):
                complexity += 1
                if child.ifs:
                    complexity += len(child.ifs)

        return complexity

    def _check_python_issues(self, tree: ast.AST, code: str) -> list[str]:
        """Check for common Python code issues."""
        issues = []

        for node in ast.walk(tree):
            # Check for bare except
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                issues.append(f"Line {node.lineno}: Bare 'except:' - consider catching specific exceptions")

            # Check for mutable default arguments
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                for default in node.args.defaults + node.args.kw_defaults:
                    if default and isinstance(default, ast.List | ast.Dict | ast.Set):
                        issues.append(f"Line {node.lineno}: Function '{node.name}' has mutable default argument")

            # Check for unused imports (basic check)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    name = alias.asname or alias.name.split(".")[0]
                    if code.count(name) == 1:
                        issues.append(f"Line {node.lineno}: Import '{alias.name}' may be unused")

        return issues

    def get_functions(self, code: str, language: str = "python") -> list[FunctionInfo]:
        """Extract detailed function information from code."""
        functions = []

        if language != "python":
            return functions

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return functions

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                args = [arg.arg for arg in node.args.args]
                returns = None
                if node.returns:
                    returns = ast.unparse(node.returns)

                docstring = ast.get_docstring(node)
                complexity = self._calculate_complexity(node)

                functions.append(FunctionInfo(
                    name=node.name,
                    args=args,
                    returns=returns,
                    docstring=docstring,
                    line_number=node.lineno,
                    complexity=complexity
                ))

        return functions

    def get_classes(self, code: str, language: str = "python") -> list[ClassInfo]:
        """Extract detailed class information from code."""
        classes = []

        if language != "python":
            return classes

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return classes

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                bases = [ast.unparse(base) for base in node.bases]
                methods = [
                    n.name for n in node.body
                    if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)
                ]
                docstring = ast.get_docstring(node)

                classes.append(ClassInfo(
                    name=node.name,
                    bases=bases,
                    methods=methods,
                    docstring=docstring,
                    line_number=node.lineno
                ))

        return classes

    def detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        suffix = Path(file_path).suffix.lower()
        return self.SUPPORTED_LANGUAGES.get(suffix, "unknown")

    def find_similar_code(self, code: str, target_code: str) -> float:
        """Calculate similarity between two code snippets."""
        # Simple token-based similarity
        def tokenize(text: str) -> set[str]:
            return set(re.findall(r"\w+", text.lower()))

        tokens1 = tokenize(code)
        tokens2 = tokenize(target_code)

        if not tokens1 or not tokens2:
            return 0.0

        intersection = tokens1 & tokens2
        union = tokens1 | tokens2

        return len(intersection) / len(union)
