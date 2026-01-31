"""CLI Interface - User interface for interacting with the AI system."""

import sys
from typing import Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from ..conversation import ConversationEngine
from ..knowledge import KnowledgeBase


class CLIInterface:
    """Command-line interface for the AI system."""

    def __init__(self, data_dir: str = "data"):
        """
        Initialize the CLI interface.

        Args:
            data_dir: Directory for storing data
        """
        self.console = Console()

        # Initialize components
        self.kb = KnowledgeBase(data_dir=data_dir)
        self.engine = ConversationEngine(self.kb)

        # Setup prompt toolkit
        self.style = Style.from_dict(
            {
                "prompt": "#00aa00 bold",
                "input": "#ffffff",
            }
        )

        try:
            self.session: Optional[PromptSession] = PromptSession(
                history=FileHistory(f"{data_dir}/.history"),
                style=self.style,
            )
        except Exception:
            self.session = None

    def run(self) -> None:
        """Run the interactive CLI."""
        self._show_welcome()

        while True:
            try:
                # Get user input
                user_input = self._get_input()

                if user_input is None:
                    continue

                # Check for exit
                if user_input.lower() in ["יציאה", "exit", "quit", "bye", "להתראות"]:
                    self._show_goodbye()
                    break

                # Process input and show response
                response = self.engine.process_input(user_input)
                self._show_response(response)

            except KeyboardInterrupt:
                self.console.print("\n")
                continue
            except EOFError:
                self._show_goodbye()
                break

    def _get_input(self) -> Optional[str]:
        """Get input from user."""
        try:
            # Show training mode indicator
            if self.engine.context.training_mode:
                prompt_text = [("class:prompt", "[אימון] ")]
            else:
                prompt_text = [("class:prompt", "אתה: ")]

            if self.session:
                user_input = self.session.prompt(prompt_text)
            else:
                # Fallback to basic input
                prefix = "[אימון] " if self.engine.context.training_mode else "אתה: "
                user_input = input(prefix)

            return user_input.strip()

        except Exception:
            return None

    def _show_welcome(self) -> None:
        """Show welcome message."""
        welcome_text = Text()
        welcome_text.append("ברוכים הבאים ל-", style="bold")
        welcome_text.append("Aiomer", style="bold cyan")
        welcome_text.append(" - מערכת AI לשיחה ולמידה\n\n", style="bold")
        welcome_text.append("פקודות בסיסיות:\n", style="yellow")
        welcome_text.append("  • ", style="dim")
        welcome_text.append("עזרה", style="green")
        welcome_text.append(" - הצג את כל הפקודות\n")
        welcome_text.append("  • ", style="dim")
        welcome_text.append("אימון", style="green")
        welcome_text.append(" - כנס למצב אימון\n")
        welcome_text.append("  • ", style="dim")
        welcome_text.append("יציאה", style="green")
        welcome_text.append(" - צא מהתוכנית\n\n")
        welcome_text.append("פשוט שאל אותי משהו כדי להתחיל!", style="italic")

        panel = Panel(
            welcome_text,
            title="[bold blue]Aiomer AI[/bold blue]",
            border_style="blue",
            padding=(1, 2),
        )
        self.console.print(panel)
        self.console.print()

    def _show_response(self, response: str) -> None:
        """Display AI response."""
        self.console.print()

        # Format response based on content
        if response.startswith("✓"):
            self.console.print(f"[green]{response}[/green]")
        elif response.startswith("✗"):
            self.console.print(f"[red]{response}[/red]")
        else:
            # Regular response
            response_text = Text()
            response_text.append("AI: ", style="bold cyan")
            response_text.append(response)
            self.console.print(response_text)

        self.console.print()

    def _show_goodbye(self) -> None:
        """Show goodbye message."""
        self.console.print()
        self.console.print("[bold blue]להתראות! 👋[/bold blue]")
        self.console.print()


def main() -> None:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Aiomer - Conversational AI System")
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory for storing data (default: data)",
    )
    args = parser.parse_args()

    cli = CLIInterface(data_dir=args.data_dir)
    cli.run()


if __name__ == "__main__":
    main()
