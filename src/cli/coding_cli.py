"""
CLI interface for the Coding Agent.
"""

import sys
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.table import Table

from ..coding_agent import CodingAgent


class CodingCLI:
    """Interactive CLI for the Coding Agent."""

    def __init__(self, language: str = "he", data_dir: str = None):
        """Initialize the CLI."""
        self.console = Console()
        self.agent = CodingAgent(language=language, data_dir=data_dir)

        # History file
        history_dir = Path.home() / ".aiomer"
        history_dir.mkdir(parents=True, exist_ok=True)
        history_file = history_dir / "coding_history.txt"

        # Prompt style
        self.style = Style.from_dict({
            'prompt': '#00aa00 bold',
            'input': '#ffffff',
        })

        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            style=self.style,
        )

        self._multiline_mode = False
        self._multiline_buffer = []

    def run(self):
        """Run the interactive CLI."""
        self._print_welcome()

        while True:
            try:
                if self._multiline_mode:
                    prompt = "... "
                else:
                    prompt = "🤖 > " if self.agent.language == "he" else "🤖 > "

                user_input = self.session.prompt(prompt)

                # Handle special commands
                if user_input.lower() in ["exit", "quit", "יציאה", "צא"]:
                    self._print_goodbye()
                    break

                if user_input.lower() in ["clear", "נקה"]:
                    self.console.clear()
                    continue

                if user_input == "```":
                    if self._multiline_mode:
                        # End multiline mode
                        code = "\n".join(self._multiline_buffer)
                        self._multiline_buffer = []
                        self._multiline_mode = False
                        user_input = code
                    else:
                        # Start multiline mode
                        self._multiline_mode = True
                        self._multiline_buffer = []
                        self.console.print("[dim]הקלד קוד (סיים עם ```):[/dim]")
                        continue

                if self._multiline_mode:
                    self._multiline_buffer.append(user_input)
                    continue

                if user_input.lower() in ["he", "en"]:
                    self.agent.set_language(user_input.lower())
                    msg = "שפה שונתה לעברית" if user_input.lower() == "he" else "Language changed to English"
                    self.console.print(f"[green]✓[/green] {msg}")
                    continue

                if user_input.startswith("file ") or user_input.startswith("קובץ "):
                    file_path = user_input.split(maxsplit=1)[1]
                    self._process_file(file_path)
                    continue

                # Process through agent
                self._process_input(user_input)

            except KeyboardInterrupt:
                self.console.print("\n[yellow]השתמש ב-'exit' או 'יציאה' כדי לצאת[/yellow]")
            except EOFError:
                break

    def _process_input(self, user_input: str):
        """Process user input and display response."""
        response = self.agent.process(user_input)

        # Display message
        if response.message:
            self.console.print()
            self.console.print(Panel(
                Markdown(response.message),
                title="🤖 עוזר תכנות" if self.agent.language == "he" else "🤖 Coding Assistant",
                border_style="blue"
            ))

        # Display code if present
        if response.code:
            self.console.print()
            syntax = Syntax(
                response.code,
                response.language,
                theme="monokai",
                line_numbers=True
            )
            self.console.print(Panel(
                syntax,
                title=f"📝 {response.language.upper()}",
                border_style="green"
            ))

        # Display metrics if present
        if response.metrics:
            self._display_metrics(response.metrics)

        # Display suggestions
        if response.suggestions:
            self.console.print()
            suggestions_text = "\n".join(f"• {s}" for s in response.suggestions)
            self.console.print(Panel(
                suggestions_text,
                title="💡 הצעות" if self.agent.language == "he" else "💡 Suggestions",
                border_style="yellow"
            ))

    def _process_file(self, file_path: str):
        """Process a file."""
        path = Path(file_path).expanduser()

        if not path.exists():
            self.console.print(f"[red]❌ הקובץ לא נמצא: {file_path}[/red]")
            return

        try:
            code = path.read_text(encoding="utf-8")
            self.agent.current_code = code
            self.agent.current_language = self.agent.analyzer.detect_language(str(path))

            # Analyze and display
            response = self.agent.process(f"נתח\n{code}")
            self._process_input("")

            self.console.print(f"[green]✓[/green] קובץ נטען: {path.name}")

        except Exception as e:
            self.console.print(f"[red]❌ שגיאה בקריאת הקובץ: {e}[/red]")

    def _display_metrics(self, metrics):
        """Display code metrics in a table."""
        table = Table(title="📊 מטריקות קוד" if self.agent.language == "he" else "📊 Code Metrics")

        table.add_column("מדד" if self.agent.language == "he" else "Metric", style="cyan")
        table.add_column("ערך" if self.agent.language == "he" else "Value", style="green")

        labels = {
            "he": {
                "lines": "שורות קוד",
                "blank": "שורות ריקות",
                "comments": "הערות",
                "functions": "פונקציות",
                "classes": "מחלקות",
                "complexity": "מורכבות"
            },
            "en": {
                "lines": "Lines of code",
                "blank": "Blank lines",
                "comments": "Comments",
                "functions": "Functions",
                "classes": "Classes",
                "complexity": "Complexity"
            }
        }

        l = labels[self.agent.language]

        table.add_row(l["lines"], str(metrics.lines_of_code))
        table.add_row(l["blank"], str(metrics.blank_lines))
        table.add_row(l["comments"], str(metrics.comment_lines))
        table.add_row(l["functions"], str(len(metrics.functions)))
        table.add_row(l["classes"], str(len(metrics.classes)))
        table.add_row(l["complexity"], str(metrics.complexity))

        self.console.print()
        self.console.print(table)

    def _print_welcome(self):
        """Print welcome message."""
        if self.agent.language == "he":
            welcome = """
╔══════════════════════════════════════════════════════════╗
║          🤖 עוזר התכנות של Aiomer                       ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  פקודות מהירות:                                          ║
║  • נתח / analyze  - ניתוח קוד                            ║
║  • הסבר / explain - הסבר קוד                             ║
║  • בדוק / review  - סקירת קוד                            ║
║  • צור / generate - יצירת קוד                            ║
║  • הרץ / run      - הרצת קוד Python                      ║
║  • עזרה / help    - עזרה מלאה                            ║
║                                                          ║
║  טיפים:                                                  ║
║  • הקלד ``` להתחלת קוד מרובה שורות                       ║
║  • file <path> לטעינת קובץ                               ║
║  • he/en להחלפת שפה                                      ║
║  • exit/יציאה ליציאה                                     ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""
        else:
            welcome = """
╔══════════════════════════════════════════════════════════╗
║          🤖 Aiomer Coding Assistant                      ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Quick commands:                                         ║
║  • analyze  - Analyze code                               ║
║  • explain  - Explain code                               ║
║  • review   - Review code                                ║
║  • generate - Generate code                              ║
║  • run      - Run Python code                            ║
║  • help     - Full help                                  ║
║                                                          ║
║  Tips:                                                   ║
║  • Type ``` to start multiline code                      ║
║  • file <path> to load a file                            ║
║  • he/en to switch language                              ║
║  • exit to quit                                          ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
"""

        self.console.print(welcome, style="bold blue")

    def _print_goodbye(self):
        """Print goodbye message."""
        if self.agent.language == "he":
            self.console.print("\n[bold green]להתראות! 👋[/bold green]")
        else:
            self.console.print("\n[bold green]Goodbye! 👋[/bold green]")


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Aiomer Coding Assistant")
    parser.add_argument("--lang", "-l", choices=["he", "en"], default="he",
                        help="Interface language (default: he)")
    parser.add_argument("--data-dir", "-d", type=str, default=None,
                        help="Data directory")

    args = parser.parse_args()

    cli = CodingCLI(language=args.lang, data_dir=args.data_dir)
    cli.run()


if __name__ == "__main__":
    main()
