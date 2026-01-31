"""
Code Explainer - Explain code in natural language.
"""

import ast
import re
from dataclasses import dataclass
from typing import Optional

from .analyzer import CodeAnalyzer


@dataclass
class CodeExplanation:
    """Explanation of code."""
    summary: str
    detailed: str
    concepts: list[str]
    suggestions: list[str]


class CodeExplainer:
    """Explains code in natural language (Hebrew/English)."""

    def __init__(self, language: str = "he"):
        """
        Initialize explainer.

        Args:
            language: Output language ("he" for Hebrew, "en" for English)
        """
        self.language = language
        self.analyzer = CodeAnalyzer()
        self._load_explanations()

    def _load_explanations(self):
        """Load explanation templates."""
        self._explanations = {
            "he": {
                "function": "פונקציה בשם '{name}' שמקבלת {args_count} פרמטרים ומחזירה {return_type}.",
                "class": "מחלקה בשם '{name}' שיורשת מ-{bases}. המחלקה מכילה {method_count} מתודות.",
                "loop_for": "לולאת for שרצה על {iterable}.",
                "loop_while": "לולאת while שממשיכה כל עוד {condition}.",
                "conditional": "תנאי if שבודק {condition}.",
                "import": "ייבוא של מודול '{module}'.",
                "try_except": "בלוק try-except לטיפול בשגיאות מסוג {exceptions}.",
                "list_comp": "list comprehension שיוצר רשימה חדשה.",
                "dict_comp": "dictionary comprehension שיוצר מילון חדש.",
                "decorator": "דקורטור '{name}' שמשנה את התנהגות הפונקציה.",
                "async": "פונקציה אסינכרונית שמאפשרת ביצוע מקבילי.",
                "context_manager": "context manager (with) לניהול משאבים.",
                "lambda": "פונקציית lambda - פונקציה אנונימית קצרה.",
                "generator": "generator שמייצר ערכים בצורה עצלה (lazy).",
                "no_code": "לא סופק קוד לניתוח.",
                "concepts": {
                    "oop": "תכנות מונחה עצמים (OOP)",
                    "async": "תכנות אסינכרוני",
                    "functional": "תכנות פונקציונלי",
                    "error_handling": "טיפול בשגיאות",
                    "file_io": "קריאה/כתיבה לקבצים",
                    "api": "עבודה עם API",
                    "database": "עבודה עם בסיס נתונים",
                    "testing": "בדיקות",
                },
                "suggestions": {
                    "add_types": "הוסף type hints לפונקציות",
                    "add_docstring": "הוסף docstring לתיעוד",
                    "split_function": "שקול לפצל את הפונקציה - היא ארוכה מדי",
                    "reduce_complexity": "הפונקציה מורכבת מדי - שקול לפשט",
                    "add_tests": "הוסף בדיקות יחידה (unit tests)",
                    "use_context_manager": "השתמש ב-context manager לניהול משאבים",
                    "avoid_global": "הימנע משימוש במשתנים גלובליים",
                },
            },
            "en": {
                "function": "A function named '{name}' that takes {args_count} parameters and returns {return_type}.",
                "class": "A class named '{name}' that inherits from {bases}. The class contains {method_count} methods.",
                "loop_for": "A for loop iterating over {iterable}.",
                "loop_while": "A while loop that continues while {condition}.",
                "conditional": "An if condition checking {condition}.",
                "import": "Import of module '{module}'.",
                "try_except": "A try-except block handling {exceptions} errors.",
                "list_comp": "A list comprehension creating a new list.",
                "dict_comp": "A dictionary comprehension creating a new dict.",
                "decorator": "A decorator '{name}' that modifies function behavior.",
                "async": "An async function enabling concurrent execution.",
                "context_manager": "A context manager (with) for resource management.",
                "lambda": "A lambda function - a short anonymous function.",
                "generator": "A generator that yields values lazily.",
                "no_code": "No code provided for analysis.",
                "concepts": {
                    "oop": "Object-Oriented Programming (OOP)",
                    "async": "Asynchronous Programming",
                    "functional": "Functional Programming",
                    "error_handling": "Error Handling",
                    "file_io": "File I/O",
                    "api": "API Integration",
                    "database": "Database Operations",
                    "testing": "Testing",
                },
                "suggestions": {
                    "add_types": "Add type hints to functions",
                    "add_docstring": "Add docstring for documentation",
                    "split_function": "Consider splitting the function - it's too long",
                    "reduce_complexity": "Function is too complex - consider simplifying",
                    "add_tests": "Add unit tests",
                    "use_context_manager": "Use context manager for resource management",
                    "avoid_global": "Avoid using global variables",
                },
            },
        }

    def explain(self, code: str, detail_level: str = "medium") -> CodeExplanation:
        """
        Explain code in natural language.

        Args:
            code: Source code to explain
            detail_level: "brief", "medium", or "detailed"

        Returns:
            CodeExplanation object
        """
        if not code.strip():
            return CodeExplanation(
                summary=self._get_text("no_code"),
                detailed="",
                concepts=[],
                suggestions=[]
            )

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return CodeExplanation(
                summary=f"Syntax error: {e}" if self.language == "en" else f"שגיאת תחביר: {e}",
                detailed=str(e),
                concepts=[],
                suggestions=[]
            )

        explanations = []
        concepts = set()
        suggestions = []

        for node in ast.walk(tree):
            exp = self._explain_node(node)
            if exp:
                explanations.append(exp)

            # Detect concepts
            concepts.update(self._detect_concepts(node))

        # Generate suggestions
        suggestions = self._generate_suggestions(tree, code)

        summary = self._create_summary(explanations, detail_level)
        detailed = self._create_detailed(explanations) if detail_level != "brief" else ""

        return CodeExplanation(
            summary=summary,
            detailed=detailed,
            concepts=[self._get_text("concepts").get(c, c) for c in concepts],
            suggestions=suggestions
        )

    def _explain_node(self, node: ast.AST) -> Optional[str]:
        """Explain a single AST node."""
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            args_count = len(node.args.args)
            return_type = ast.unparse(node.returns) if node.returns else "None"
            prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
            return f"{prefix}" + self._get_text("function").format(
                name=node.name,
                args_count=args_count,
                return_type=return_type
            )

        elif isinstance(node, ast.ClassDef):
            bases = ", ".join(ast.unparse(b) for b in node.bases) or "object"
            methods = [n for n in node.body if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef)]
            return self._get_text("class").format(
                name=node.name,
                bases=bases,
                method_count=len(methods)
            )

        elif isinstance(node, ast.For):
            iterable = ast.unparse(node.iter)
            return self._get_text("loop_for").format(iterable=iterable)

        elif isinstance(node, ast.While):
            condition = ast.unparse(node.test)
            return self._get_text("loop_while").format(condition=condition)

        elif isinstance(node, ast.If) and not self._is_elif(node):
            condition = ast.unparse(node.test)
            return self._get_text("conditional").format(condition=condition)

        elif isinstance(node, ast.Import):
            modules = ", ".join(alias.name for alias in node.names)
            return self._get_text("import").format(module=modules)

        elif isinstance(node, ast.ImportFrom):
            return self._get_text("import").format(module=f"{node.module}")

        elif isinstance(node, ast.Try):
            exceptions = [ast.unparse(h.type) if h.type else "Exception" for h in node.handlers]
            return self._get_text("try_except").format(exceptions=", ".join(exceptions))

        elif isinstance(node, ast.ListComp):
            return self._get_text("list_comp")

        elif isinstance(node, ast.DictComp):
            return self._get_text("dict_comp")

        elif isinstance(node, ast.Lambda):
            return self._get_text("lambda")

        return None

    def _is_elif(self, node: ast.If) -> bool:
        """Check if an If node is an elif."""
        return hasattr(node, "_is_elif") and node._is_elif

    def _detect_concepts(self, node: ast.AST) -> set[str]:
        """Detect programming concepts in a node."""
        concepts = set()

        if isinstance(node, ast.ClassDef):
            concepts.add("oop")

        if isinstance(node, ast.AsyncFunctionDef | ast.Await):
            concepts.add("async")

        if isinstance(node, ast.Lambda | ast.ListComp | ast.DictComp | ast.SetComp | ast.GeneratorExp):
            concepts.add("functional")

        if isinstance(node, ast.Try):
            concepts.add("error_handling")

        if isinstance(node, ast.With):
            # Check for file operations
            if any("open" in ast.unparse(item.context_expr) for item in node.items):
                concepts.add("file_io")

        if isinstance(node, ast.Call):
            call_name = ast.unparse(node.func)
            if any(api in call_name for api in ["requests", "httpx", "aiohttp", "fetch"]):
                concepts.add("api")
            if any(db in call_name for db in ["execute", "query", "session", "cursor"]):
                concepts.add("database")

        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            concepts.add("testing")

        return concepts

    def _generate_suggestions(self, tree: ast.AST, code: str) -> list[str]:
        """Generate improvement suggestions."""
        suggestions = []
        texts = self._get_text("suggestions")

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Check for type hints
                if not node.returns and not any(arg.annotation for arg in node.args.args):
                    suggestions.append(texts["add_types"])

                # Check for docstring
                if not ast.get_docstring(node):
                    suggestions.append(texts["add_docstring"])

                # Check complexity
                metrics = self.analyzer.analyze_code(ast.unparse(node))
                if metrics.complexity > 10:
                    suggestions.append(texts["reduce_complexity"])

                # Check function length
                func_lines = ast.unparse(node).count("\n")
                if func_lines > 50:
                    suggestions.append(texts["split_function"])

            # Check for global usage
            if isinstance(node, ast.Global):
                suggestions.append(texts["avoid_global"])

        return list(set(suggestions))[:5]  # Limit to 5 unique suggestions

    def _create_summary(self, explanations: list[str], detail_level: str) -> str:
        """Create a summary from explanations."""
        if not explanations:
            return self._get_text("no_code")

        if detail_level == "brief":
            return explanations[0] if explanations else ""

        # Group and summarize
        if self.language == "he":
            return f"הקוד מכיל: " + " ".join(explanations[:3])
        return f"The code contains: " + " ".join(explanations[:3])

    def _create_detailed(self, explanations: list[str]) -> str:
        """Create detailed explanation."""
        if self.language == "he":
            header = "פירוט מלא:\n"
        else:
            header = "Full details:\n"

        return header + "\n".join(f"• {exp}" for exp in explanations)

    def _get_text(self, key: str):
        """Get text in current language."""
        return self._explanations.get(self.language, self._explanations["en"]).get(key, key)

    def explain_error(self, error: Exception, code: str = "") -> str:
        """Explain a Python error in natural language."""
        error_type = type(error).__name__
        error_msg = str(error)

        explanations = {
            "he": {
                "SyntaxError": f"שגיאת תחביר: הקוד לא תקין מבחינת התחביר של Python. {error_msg}",
                "IndentationError": f"שגיאת הזחה: יש בעיה ברווחים/טאבים בקוד. {error_msg}",
                "NameError": f"שגיאת שם: משתנה או פונקציה '{error_msg.split(chr(39))[1] if chr(39) in error_msg else ''}' לא מוגדרים.",
                "TypeError": f"שגיאת טיפוס: פעולה על טיפוס לא מתאים. {error_msg}",
                "ValueError": f"שגיאת ערך: הערך שהועבר לא תקין. {error_msg}",
                "IndexError": f"שגיאת אינדקס: ניסיון לגשת לאינדקס שלא קיים ברשימה. {error_msg}",
                "KeyError": f"שגיאת מפתח: המפתח לא קיים במילון. {error_msg}",
                "AttributeError": f"שגיאת תכונה: האובייקט לא מכיל את התכונה המבוקשת. {error_msg}",
                "ImportError": f"שגיאת ייבוא: לא ניתן לייבא את המודול. {error_msg}",
                "FileNotFoundError": f"הקובץ לא נמצא: {error_msg}",
                "ZeroDivisionError": "שגיאת חילוק באפס: לא ניתן לחלק באפס.",
            },
            "en": {
                "SyntaxError": f"Syntax Error: The code has invalid Python syntax. {error_msg}",
                "IndentationError": f"Indentation Error: There's an issue with spaces/tabs in the code. {error_msg}",
                "NameError": f"Name Error: Variable or function is not defined. {error_msg}",
                "TypeError": f"Type Error: Operation on incompatible type. {error_msg}",
                "ValueError": f"Value Error: Invalid value passed. {error_msg}",
                "IndexError": f"Index Error: Trying to access index that doesn't exist. {error_msg}",
                "KeyError": f"Key Error: The key doesn't exist in the dictionary. {error_msg}",
                "AttributeError": f"Attribute Error: Object doesn't have the requested attribute. {error_msg}",
                "ImportError": f"Import Error: Cannot import the module. {error_msg}",
                "FileNotFoundError": f"File not found: {error_msg}",
                "ZeroDivisionError": "Division by zero error: Cannot divide by zero.",
            },
        }

        lang_explanations = explanations.get(self.language, explanations["en"])
        return lang_explanations.get(error_type, f"{error_type}: {error_msg}")

    def set_language(self, language: str):
        """Set output language."""
        if language in ["he", "en"]:
            self.language = language

    def explain_line(self, code: str, line_number: int) -> str:
        """Explain a specific line of code."""
        lines = code.split("\n")
        if line_number < 1 or line_number > len(lines):
            if self.language == "he":
                return f"שורה {line_number} לא קיימת בקוד."
            return f"Line {line_number} doesn't exist in the code."

        line = lines[line_number - 1].strip()

        # Try to parse and explain
        try:
            tree = ast.parse(line)
            for node in ast.walk(tree):
                exp = self._explain_node(node)
                if exp:
                    return f"שורה {line_number}: {exp}" if self.language == "he" else f"Line {line_number}: {exp}"
        except SyntaxError:
            pass

        # Pattern-based explanation for common constructs
        patterns = {
            r"^\s*#": ("תגובה (comment)", "Comment"),
            r"^\s*return\s": ("משפט return - מחזיר ערך מהפונקציה", "Return statement - returns value from function"),
            r"^\s*yield\s": ("משפט yield - מייצר ערך מ-generator", "Yield statement - produces value from generator"),
            r"^\s*raise\s": ("זריקת שגיאה (exception)", "Raising an exception"),
            r"^\s*pass\s*$": ("משפט pass - placeholder ריק", "Pass statement - empty placeholder"),
            r"^\s*break\s*$": ("יציאה מלולאה", "Breaking out of loop"),
            r"^\s*continue\s*$": ("מעבר לאיטרציה הבאה", "Continue to next iteration"),
            r"=": ("השמה לא משתנה", "Variable assignment"),
        }

        for pattern, (he_exp, en_exp) in patterns.items():
            if re.search(pattern, line):
                exp = he_exp if self.language == "he" else en_exp
                return f"שורה {line_number}: {exp}" if self.language == "he" else f"Line {line_number}: {exp}"

        return f"שורה {line_number}: {line}" if self.language == "he" else f"Line {line_number}: {line}"
