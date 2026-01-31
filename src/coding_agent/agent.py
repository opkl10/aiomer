"""
Coding Agent - Main AI coding assistant.
Combines analysis, generation, explanation, and debugging capabilities.
"""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Any
from datetime import datetime

from .analyzer import CodeAnalyzer, CodeMetrics
from .generator import CodeGenerator, GeneratedCode
from .explainer import CodeExplainer, CodeExplanation


@dataclass
class AgentResponse:
    """Response from the coding agent."""
    message: str
    code: Optional[str] = None
    language: str = "python"
    suggestions: list[str] = field(default_factory=list)
    metrics: Optional[CodeMetrics] = None
    success: bool = True


@dataclass
class ConversationMessage:
    """A message in the agent conversation."""
    role: str  # "user" or "assistant"
    content: str
    code: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class CodingAgent:
    """
    AI-powered coding assistant that helps with:
    - Code analysis and review
    - Code generation
    - Code explanation
    - Debugging assistance
    - Best practices suggestions
    """

    COMMANDS = {
        # Hebrew commands
        "נתח": "analyze",
        "צור": "generate",
        "הסבר": "explain",
        "בדוק": "review",
        "תקן": "fix",
        "מטריקות": "metrics",
        "תבנית": "pattern",
        "טסט": "test",
        "עזרה": "help",
        # English commands
        "analyze": "analyze",
        "generate": "generate",
        "explain": "explain",
        "review": "review",
        "fix": "fix",
        "metrics": "metrics",
        "pattern": "pattern",
        "test": "test",
        "help": "help",
        "run": "run",
        "הרץ": "run",
    }

    def __init__(self, language: str = "he", data_dir: Optional[str] = None):
        """
        Initialize the coding agent.

        Args:
            language: Output language ("he" for Hebrew, "en" for English)
            data_dir: Directory for storing data
        """
        self.language = language
        self.data_dir = Path(data_dir) if data_dir else Path.home() / ".aiomer"
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.analyzer = CodeAnalyzer()
        self.generator = CodeGenerator()
        self.explainer = CodeExplainer(language)

        self.conversation: list[ConversationMessage] = []
        self.current_code: Optional[str] = None
        self.current_language: str = "python"

        self._help_messages = self._init_help_messages()

    def _init_help_messages(self) -> dict[str, str]:
        """Initialize help messages."""
        return {
            "he": """
🤖 סוכן עוזר תכנות - פקודות זמינות:

📊 ניתוח קוד:
  • נתח <קוד>     - ניתוח סטטי של הקוד
  • מטריקות       - הצג מטריקות של הקוד הנוכחי
  • בדוק <קוד>    - סקירת קוד ובדיקת בעיות

📝 יצירת קוד:
  • צור פונקציה <שם> - יצירת פונקציה חדשה
  • צור מחלקה <שם>   - יצירת מחלקה חדשה
  • תבנית <שם>       - יצירת design pattern

📖 הסברים:
  • הסבר <קוד>    - הסבר הקוד בשפה פשוטה
  • הסבר שורה <מספר> - הסבר שורה ספציפית

🔧 תיקונים:
  • תקן <קוד>     - הצע תיקונים לקוד
  • טסט <שם>      - יצירת unit tests

▶️ הרצה:
  • הרץ <קוד>     - הרץ קוד Python

💡 טיפים:
  • אפשר לשלוח קוד ישירות ואני אנסה להבין מה אתה רוצה
  • כל קוד שתשלח יישמר כ"קוד נוכחי" לפעולות נוספות
""",
            "en": """
🤖 Coding Assistant Agent - Available Commands:

📊 Code Analysis:
  • analyze <code>  - Static code analysis
  • metrics         - Show current code metrics
  • review <code>   - Code review and issue detection

📝 Code Generation:
  • generate function <name> - Create new function
  • generate class <name>    - Create new class
  • pattern <name>           - Create design pattern

📖 Explanations:
  • explain <code>      - Explain code in plain language
  • explain line <num>  - Explain specific line

🔧 Fixes:
  • fix <code>    - Suggest code fixes
  • test <name>   - Generate unit tests

▶️ Execution:
  • run <code>    - Run Python code

💡 Tips:
  • You can send code directly and I'll try to understand what you want
  • Any code you send will be saved as "current code" for further actions
""",
        }

    def process(self, user_input: str) -> AgentResponse:
        """
        Process user input and return appropriate response.

        Args:
            user_input: User message or code

        Returns:
            AgentResponse with message and optional code
        """
        # Save to conversation
        self.conversation.append(ConversationMessage(role="user", content=user_input))

        # Check for commands
        command, args = self._parse_command(user_input)

        if command:
            response = self._execute_command(command, args)
        else:
            # Try to understand what the user wants
            response = self._smart_process(user_input)

        # Save response to conversation
        self.conversation.append(ConversationMessage(
            role="assistant",
            content=response.message,
            code=response.code
        ))

        return response

    def _parse_command(self, text: str) -> tuple[Optional[str], str]:
        """Parse command from user input."""
        text = text.strip()

        for cmd_text, cmd_name in self.COMMANDS.items():
            if text.lower().startswith(cmd_text):
                args = text[len(cmd_text):].strip()
                return cmd_name, args

        return None, text

    def _execute_command(self, command: str, args: str) -> AgentResponse:
        """Execute a command."""
        handlers = {
            "analyze": self._cmd_analyze,
            "generate": self._cmd_generate,
            "explain": self._cmd_explain,
            "review": self._cmd_review,
            "fix": self._cmd_fix,
            "metrics": self._cmd_metrics,
            "pattern": self._cmd_pattern,
            "test": self._cmd_test,
            "help": self._cmd_help,
            "run": self._cmd_run,
        }

        handler = handlers.get(command, self._cmd_unknown)
        return handler(args)

    def _smart_process(self, text: str) -> AgentResponse:
        """Intelligently process text without explicit command."""
        # Check if it's code
        if self._looks_like_code(text):
            self.current_code = text
            self.current_language = self._detect_language(text)

            # Analyze and explain
            metrics = self.analyzer.analyze_code(text, self.current_language)
            explanation = self.explainer.explain(text, "medium")

            if self.language == "he":
                msg = f"קיבלתי את הקוד! 📝\n\n{explanation.summary}\n\n"
                if metrics.issues:
                    msg += "⚠️ בעיות שנמצאו:\n" + "\n".join(f"  • {i}" for i in metrics.issues[:3])
                if explanation.suggestions:
                    msg += "\n\n💡 הצעות:\n" + "\n".join(f"  • {s}" for s in explanation.suggestions[:3])
                msg += "\n\nמה תרצה לעשות עם הקוד? (הסבר / נתח / תקן / הרץ)"
            else:
                msg = f"Got the code! 📝\n\n{explanation.summary}\n\n"
                if metrics.issues:
                    msg += "⚠️ Issues found:\n" + "\n".join(f"  • {i}" for i in metrics.issues[:3])
                if explanation.suggestions:
                    msg += "\n\n💡 Suggestions:\n" + "\n".join(f"  • {s}" for s in explanation.suggestions[:3])
                msg += "\n\nWhat would you like to do? (explain / analyze / fix / run)"

            return AgentResponse(
                message=msg,
                code=text,
                language=self.current_language,
                suggestions=explanation.suggestions,
                metrics=metrics
            )

        # Check for questions about the current code
        if self.current_code:
            question_words = ["מה", "איך", "למה", "what", "how", "why", "?"]
            if any(w in text.lower() for w in question_words):
                return self._answer_question(text)

        # Default: show help
        if self.language == "he":
            return AgentResponse(message="לא הבנתי. הנה מה שאני יכול לעשות:\n" + self._help_messages["he"])
        return AgentResponse(message="I didn't understand. Here's what I can do:\n" + self._help_messages["en"])

    def _looks_like_code(self, text: str) -> bool:
        """Check if text looks like code."""
        code_indicators = [
            r"\bdef\s+\w+\s*\(",
            r"\bclass\s+\w+",
            r"\bimport\s+\w+",
            r"\bfunction\s+\w+",
            r"\bconst\s+\w+\s*=",
            r"\blet\s+\w+\s*=",
            r"\bvar\s+\w+\s*=",
            r"^\s*for\s+\w+\s+in\s+",
            r"^\s*if\s+.+:",
            r"^\s*while\s+.+:",
            r"=>\s*{",
            r"\breturn\s+",
        ]

        for pattern in code_indicators:
            if re.search(pattern, text, re.MULTILINE):
                return True

        # Check for multiple lines with consistent indentation
        lines = text.split("\n")
        if len(lines) > 2:
            indented_lines = sum(1 for l in lines if l.startswith(("    ", "\t")))
            if indented_lines > len(lines) * 0.3:
                return True

        return False

    def _detect_language(self, code: str) -> str:
        """Detect programming language from code."""
        patterns = {
            "python": [r"\bdef\s+\w+", r"\bimport\s+\w+", r":\s*$", r"\bself\b"],
            "javascript": [r"\bfunction\s+\w+", r"\bconst\s+", r"\blet\s+", r"=>\s*{"],
            "typescript": [r":\s*(string|number|boolean)", r"\binterface\s+", r"<\w+>"],
            "java": [r"\bpublic\s+class", r"\bprivate\s+", r"\bvoid\s+"],
            "go": [r"\bfunc\s+", r"\bpackage\s+", r":="],
            "rust": [r"\bfn\s+", r"\blet\s+mut", r"\bimpl\s+"],
        }

        scores = {lang: 0 for lang in patterns}

        for lang, lang_patterns in patterns.items():
            for pattern in lang_patterns:
                if re.search(pattern, code):
                    scores[lang] += 1

        best_match = max(scores, key=scores.get)
        return best_match if scores[best_match] > 0 else "python"

    def _answer_question(self, question: str) -> AgentResponse:
        """Answer a question about the current code."""
        if not self.current_code:
            if self.language == "he":
                return AgentResponse(message="אין קוד נוכחי. שלח לי קוד קודם.")
            return AgentResponse(message="No current code. Send me some code first.")

        explanation = self.explainer.explain(self.current_code, "detailed")

        if self.language == "he":
            msg = f"לגבי הקוד הנוכחי:\n\n{explanation.detailed}"
        else:
            msg = f"About the current code:\n\n{explanation.detailed}"

        return AgentResponse(message=msg, code=self.current_code)

    # Command handlers
    def _cmd_analyze(self, args: str) -> AgentResponse:
        """Analyze code."""
        code = args if args else self.current_code

        if not code:
            msg = "שלח לי קוד לניתוח." if self.language == "he" else "Send me code to analyze."
            return AgentResponse(message=msg, success=False)

        self.current_code = code
        metrics = self.analyzer.analyze_code(code)

        if self.language == "he":
            msg = f"""📊 תוצאות ניתוח:

📏 שורות קוד: {metrics.lines_of_code}
📝 שורות ריקות: {metrics.blank_lines}
💬 שורות הערות: {metrics.comment_lines}
🔧 פונקציות: {len(metrics.functions)} ({', '.join(metrics.functions[:5])})
📦 מחלקות: {len(metrics.classes)} ({', '.join(metrics.classes[:5])})
📥 imports: {len(metrics.imports)}
🔀 מורכבות: {metrics.complexity}
"""
            if metrics.issues:
                msg += "\n⚠️ בעיות:\n" + "\n".join(f"  • {i}" for i in metrics.issues)
        else:
            msg = f"""📊 Analysis Results:

📏 Lines of code: {metrics.lines_of_code}
📝 Blank lines: {metrics.blank_lines}
💬 Comment lines: {metrics.comment_lines}
🔧 Functions: {len(metrics.functions)} ({', '.join(metrics.functions[:5])})
📦 Classes: {len(metrics.classes)} ({', '.join(metrics.classes[:5])})
📥 Imports: {len(metrics.imports)}
🔀 Complexity: {metrics.complexity}
"""
            if metrics.issues:
                msg += "\n⚠️ Issues:\n" + "\n".join(f"  • {i}" for i in metrics.issues)

        return AgentResponse(message=msg, code=code, metrics=metrics)

    def _cmd_generate(self, args: str) -> AgentResponse:
        """Generate code."""
        parts = args.split(maxsplit=1)
        if len(parts) < 2:
            if self.language == "he":
                msg = "שימוש: צור פונקציה/מחלקה <שם>\nדוגמה: צור פונקציה calculate_sum"
            else:
                msg = "Usage: generate function/class <name>\nExample: generate function calculate_sum"
            return AgentResponse(message=msg)

        gen_type, name = parts

        if gen_type in ["פונקציה", "function", "func"]:
            result = self.generator.generate_function(
                name=name,
                args=[("param1", "Any"), ("param2", "Any")],
                return_type="Any",
                description=f"Function {name}",
                body="# TODO: Implement\n    pass"
            )
        elif gen_type in ["מחלקה", "class"]:
            result = self.generator.generate_class(
                name=name,
                attributes=[("name", "str")],
                methods=["process", "validate"],
                description=f"Class {name}"
            )
        else:
            if self.language == "he":
                msg = f"לא מכיר את הסוג '{gen_type}'. אפשרויות: פונקציה, מחלקה"
            else:
                msg = f"Unknown type '{gen_type}'. Options: function, class"
            return AgentResponse(message=msg)

        self.current_code = result.code

        if self.language == "he":
            msg = f"יצרתי {gen_type} בשם {name}! 🎉"
        else:
            msg = f"Created {gen_type} named {name}! 🎉"

        if result.imports:
            msg += "\n\nImports needed:\n" + "\n".join(result.imports)

        return AgentResponse(message=msg, code=result.code)

    def _cmd_explain(self, args: str) -> AgentResponse:
        """Explain code."""
        # Check for line explanation
        line_match = re.match(r"(?:שורה|line)\s+(\d+)", args)
        if line_match and self.current_code:
            line_num = int(line_match.group(1))
            explanation = self.explainer.explain_line(self.current_code, line_num)
            return AgentResponse(message=explanation)

        code = args if args else self.current_code

        if not code:
            msg = "שלח לי קוד להסבר." if self.language == "he" else "Send me code to explain."
            return AgentResponse(message=msg, success=False)

        self.current_code = code
        explanation = self.explainer.explain(code, "detailed")

        msg = f"{explanation.summary}\n\n{explanation.detailed}"

        if explanation.concepts:
            if self.language == "he":
                msg += "\n\n📚 קונספטים בקוד:\n" + "\n".join(f"  • {c}" for c in explanation.concepts)
            else:
                msg += "\n\n📚 Concepts in code:\n" + "\n".join(f"  • {c}" for c in explanation.concepts)

        return AgentResponse(message=msg, code=code, suggestions=explanation.suggestions)

    def _cmd_review(self, args: str) -> AgentResponse:
        """Review code."""
        code = args if args else self.current_code

        if not code:
            msg = "שלח לי קוד לסקירה." if self.language == "he" else "Send me code to review."
            return AgentResponse(message=msg, success=False)

        self.current_code = code
        metrics = self.analyzer.analyze_code(code)
        explanation = self.explainer.explain(code)

        if self.language == "he":
            msg = "📋 סקירת קוד:\n\n"

            # Quality score
            score = 100
            if metrics.issues:
                score -= len(metrics.issues) * 10
            if metrics.complexity > 10:
                score -= (metrics.complexity - 10) * 5
            if not metrics.comment_lines:
                score -= 10
            score = max(0, score)

            msg += f"⭐ ציון איכות: {score}/100\n\n"

            if metrics.issues:
                msg += "⚠️ בעיות שנמצאו:\n" + "\n".join(f"  • {i}" for i in metrics.issues) + "\n\n"

            if explanation.suggestions:
                msg += "💡 הצעות לשיפור:\n" + "\n".join(f"  • {s}" for s in explanation.suggestions)
            else:
                msg += "✅ הקוד נראה טוב!"
        else:
            msg = "📋 Code Review:\n\n"

            score = 100
            if metrics.issues:
                score -= len(metrics.issues) * 10
            if metrics.complexity > 10:
                score -= (metrics.complexity - 10) * 5
            if not metrics.comment_lines:
                score -= 10
            score = max(0, score)

            msg += f"⭐ Quality Score: {score}/100\n\n"

            if metrics.issues:
                msg += "⚠️ Issues found:\n" + "\n".join(f"  • {i}" for i in metrics.issues) + "\n\n"

            if explanation.suggestions:
                msg += "💡 Suggestions:\n" + "\n".join(f"  • {s}" for s in explanation.suggestions)
            else:
                msg += "✅ Code looks good!"

        return AgentResponse(message=msg, code=code, metrics=metrics, suggestions=explanation.suggestions)

    def _cmd_fix(self, args: str) -> AgentResponse:
        """Suggest fixes for code."""
        code = args if args else self.current_code

        if not code:
            msg = "שלח לי קוד לתיקון." if self.language == "he" else "Send me code to fix."
            return AgentResponse(message=msg, success=False)

        self.current_code = code
        metrics = self.analyzer.analyze_code(code)

        if not metrics.issues:
            msg = "לא נמצאו בעיות בקוד! ✅" if self.language == "he" else "No issues found in the code! ✅"
            return AgentResponse(message=msg, code=code)

        if self.language == "he":
            msg = "🔧 בעיות ותיקונים מוצעים:\n\n"
            for issue in metrics.issues:
                msg += f"❌ {issue}\n"
                # Add fix suggestion based on issue type
                if "Bare 'except'" in issue:
                    msg += "   ✅ תיקון: except Exception as e:\n\n"
                elif "mutable default" in issue:
                    msg += "   ✅ תיקון: השתמש ב-None כברירת מחדל ואתחל בתוך הפונקציה\n\n"
                elif "unused" in issue.lower():
                    msg += "   ✅ תיקון: הסר את ה-import או השתמש בו\n\n"
        else:
            msg = "🔧 Issues and suggested fixes:\n\n"
            for issue in metrics.issues:
                msg += f"❌ {issue}\n"
                if "Bare 'except'" in issue:
                    msg += "   ✅ Fix: Use 'except Exception as e:'\n\n"
                elif "mutable default" in issue:
                    msg += "   ✅ Fix: Use None as default and initialize inside function\n\n"
                elif "unused" in issue.lower():
                    msg += "   ✅ Fix: Remove the import or use it\n\n"

        return AgentResponse(message=msg, code=code, metrics=metrics)

    def _cmd_metrics(self, args: str) -> AgentResponse:
        """Show metrics for current code."""
        return self._cmd_analyze(args)

    def _cmd_pattern(self, args: str) -> AgentResponse:
        """Generate a design pattern."""
        if not args:
            patterns = self.generator.list_patterns()
            if self.language == "he":
                msg = "תבניות עיצוב זמינות:\n" + "\n".join(f"  • {p}" for p in patterns)
                msg += "\n\nשימוש: תבנית <שם> <שם_מחלקה>"
            else:
                msg = "Available design patterns:\n" + "\n".join(f"  • {p}" for p in patterns)
                msg += "\n\nUsage: pattern <name> <class_name>"
            return AgentResponse(message=msg)

        parts = args.split()
        pattern_name = parts[0]
        class_name = parts[1] if len(parts) > 1 else "MyClass"

        result = self.generator.generate_pattern(pattern_name, class_name)
        self.current_code = result.code

        if self.language == "he":
            msg = f"יצרתי תבנית {pattern_name} עבור {class_name}! 🎉"
        else:
            msg = f"Created {pattern_name} pattern for {class_name}! 🎉"

        if result.imports:
            msg += "\n\nImports needed:\n" + "\n".join(result.imports)

        return AgentResponse(message=msg, code=result.code)

    def _cmd_test(self, args: str) -> AgentResponse:
        """Generate tests."""
        if not args and not self.current_code:
            msg = "שלח שם פונקציה או קוד ליצירת טסטים." if self.language == "he" else "Send function name or code to generate tests."
            return AgentResponse(message=msg)

        # If we have current code, extract function names
        if self.current_code:
            functions = self.analyzer.get_functions(self.current_code)
            if functions:
                func = functions[0]
                result = self.generator.generate_test(
                    function_name=func.name,
                    description=func.docstring or f"Test {func.name}",
                    test_cases=[
                        {"name": "basic", "inputs": {"x": 1}, "expected": None},
                        {"name": "edge_case", "inputs": {"x": 0}, "expected": None},
                    ]
                )

                if self.language == "he":
                    msg = f"יצרתי טסטים לפונקציה {func.name}! 🧪\n\nשים לב: עדכן את הערכים הצפויים (expected) לפי הלוגיקה של הפונקציה."
                else:
                    msg = f"Created tests for function {func.name}! 🧪\n\nNote: Update the expected values according to your function logic."

                return AgentResponse(message=msg, code=result.code)

        msg = "לא מצאתי פונקציות בקוד." if self.language == "he" else "No functions found in the code."
        return AgentResponse(message=msg)

    def _cmd_run(self, args: str) -> AgentResponse:
        """Run Python code."""
        code = args if args else self.current_code

        if not code:
            msg = "שלח לי קוד להרצה." if self.language == "he" else "Send me code to run."
            return AgentResponse(message=msg, success=False)

        try:
            # Run in subprocess for safety
            result = subprocess.run(
                ["python3", "-c", code],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                output = result.stdout or "(no output)"
                if self.language == "he":
                    msg = f"✅ הקוד רץ בהצלחה!\n\n📤 פלט:\n{output}"
                else:
                    msg = f"✅ Code ran successfully!\n\n📤 Output:\n{output}"
            else:
                error = result.stderr
                explanation = self.explainer.explain_error(Exception(error))
                if self.language == "he":
                    msg = f"❌ שגיאה בהרצה:\n{error}\n\n💡 הסבר: {explanation}"
                else:
                    msg = f"❌ Execution error:\n{error}\n\n💡 Explanation: {explanation}"

            return AgentResponse(message=msg, code=code, success=result.returncode == 0)

        except subprocess.TimeoutExpired:
            msg = "⏰ הקוד לקח יותר מדי זמן (מעל 10 שניות)" if self.language == "he" else "⏰ Code took too long (over 10 seconds)"
            return AgentResponse(message=msg, code=code, success=False)
        except Exception as e:
            msg = f"❌ שגיאה: {e}" if self.language == "he" else f"❌ Error: {e}"
            return AgentResponse(message=msg, code=code, success=False)

    def _cmd_help(self, args: str) -> AgentResponse:
        """Show help message."""
        return AgentResponse(message=self._help_messages[self.language])

    def _cmd_unknown(self, args: str) -> AgentResponse:
        """Handle unknown command."""
        msg = "פקודה לא מוכרת. הקלד 'עזרה' לרשימת פקודות." if self.language == "he" else "Unknown command. Type 'help' for command list."
        return AgentResponse(message=msg)

    def set_language(self, language: str):
        """Set output language."""
        if language in ["he", "en"]:
            self.language = language
            self.explainer.set_language(language)

    def clear_conversation(self):
        """Clear conversation history."""
        self.conversation.clear()
        self.current_code = None

    def get_conversation_summary(self) -> str:
        """Get summary of current conversation."""
        if not self.conversation:
            return "No conversation yet." if self.language == "en" else "אין שיחה עדיין."

        msg_count = len(self.conversation)
        code_count = sum(1 for m in self.conversation if m.code)

        if self.language == "he":
            return f"📊 סיכום שיחה: {msg_count} הודעות, {code_count} קטעי קוד"
        return f"📊 Conversation summary: {msg_count} messages, {code_count} code snippets"
