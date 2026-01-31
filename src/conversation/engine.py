"""Conversation Engine - Handles natural language interaction."""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from ..knowledge import KnowledgeBase, Trainer


@dataclass
class Message:
    """Represents a conversation message."""

    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConversationContext:
    """Holds conversation context and history."""

    messages: list[Message] = field(default_factory=list)
    current_topic: Optional[str] = None
    training_mode: bool = False

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the history."""
        self.messages.append(Message(role=role, content=content))

    def get_recent_messages(self, n: int = 5) -> list[Message]:
        """Get the n most recent messages."""
        return self.messages[-n:] if self.messages else []

    def clear(self) -> None:
        """Clear conversation history."""
        self.messages = []
        self.current_topic = None
        self.training_mode = False


class ConversationEngine:
    """Main conversation engine that processes user input and generates responses."""

    def __init__(self, knowledge_base: KnowledgeBase):
        """
        Initialize the conversation engine.

        Args:
            knowledge_base: The knowledge base for retrieval
        """
        self.kb = knowledge_base
        self.trainer = Trainer(knowledge_base)
        self.context = ConversationContext()

        # Command patterns
        self.commands = {
            "עזרה": self._cmd_help,
            "help": self._cmd_help,
            "אימון": self._cmd_training_mode,
            "train": self._cmd_training_mode,
            "סטטוס": self._cmd_status,
            "status": self._cmd_status,
            "נקה": self._cmd_clear,
            "clear": self._cmd_clear,
            "חפש": self._cmd_search,
            "search": self._cmd_search,
            "יצוא": self._cmd_export,
            "export": self._cmd_export,
            "ייבוא": self._cmd_import,
            "import": self._cmd_import,
        }

    def process_input(self, user_input: str) -> str:
        """
        Process user input and generate a response.

        Args:
            user_input: The user's input text

        Returns:
            The assistant's response
        """
        user_input = user_input.strip()

        if not user_input:
            return "לא קיבלתי קלט. במה אוכל לעזור?"

        # Add to conversation history
        self.context.add_message("user", user_input)

        # Check for commands
        response = self._check_commands(user_input)
        if response:
            self.context.add_message("assistant", response)
            return response

        # Handle training mode
        if self.context.training_mode:
            response = self._handle_training(user_input)
            self.context.add_message("assistant", response)
            return response

        # Regular conversation - search knowledge and respond
        response = self._generate_response(user_input)
        self.context.add_message("assistant", response)
        return response

    def _check_commands(self, user_input: str) -> Optional[str]:
        """Check if input is a command and execute it."""
        # Check for exact command
        lower_input = user_input.lower()

        for cmd, handler in self.commands.items():
            if lower_input == cmd or lower_input.startswith(f"{cmd} "):
                args = user_input[len(cmd) :].strip() if len(user_input) > len(cmd) else ""
                return handler(args)

        return None

    def _generate_response(self, query: str) -> str:
        """Generate a response based on knowledge base search."""
        # Search for relevant knowledge
        results = self.kb.search(query, n_results=3)

        if not results:
            return self._no_knowledge_response(query)

        # Build response from top results
        response_parts = []

        for result in results:
            content = result["content"]
            score = result["score"]

            if score > 0.7:
                response_parts.append(content)
            elif score > 0.5:
                response_parts.append(f"מידע קשור: {content}")

        if response_parts:
            return "\n\n".join(response_parts)

        return self._no_knowledge_response(query)

    def _no_knowledge_response(self, query: str) -> str:
        """Generate response when no relevant knowledge is found."""
        suggestions = [
            "אין לי מידע על הנושא הזה עדיין.",
            "תוכל ללמד אותי על ידי כתיבת 'אימון' ואז להזין מידע חדש.",
            f"או שתוכל לשאול אותי משהו אחר.",
        ]
        return "\n".join(suggestions)

    def _handle_training(self, user_input: str) -> str:
        """Handle input in training mode."""
        # Check for exit training mode
        if user_input.lower() in ["סיום", "יציאה", "exit", "done"]:
            self.context.training_mode = False
            stats = self.trainer.get_training_stats()
            return f"יצאתי ממצב אימון. סה\"כ {stats['total_entries']} פריטי ידע במערכת."

        # Process training input
        result = self.trainer.train_interactive(user_input)

        if result["status"] == "success":
            return f"✓ {result['message']}"
        else:
            return f"✗ {result['message']}"

    # Command handlers

    def _cmd_help(self, args: str) -> str:
        """Show help message."""
        return """
פקודות זמינות:
  עזרה / help     - הצג הודעה זו
  אימון / train   - כנס למצב אימון
  סטטוס / status  - הצג סטטיסטיקות
  חפש <מילה>      - חפש במאגר הידע
  נקה / clear     - נקה היסטוריית שיחה
  יצוא <קובץ>     - ייצא ידע לקובץ JSON
  ייבוא <קובץ>    - ייבא ידע מקובץ JSON

במצב אימון:
  למד: <עובדה>           - למד עובדה חדשה
  ש: <שאלה> ת: <תשובה>  - למד שאלה ותשובה
  קובץ: <נתיב>          - למד מקובץ
  סיום / exit           - צא ממצב אימון
""".strip()

    def _cmd_training_mode(self, args: str) -> str:
        """Enter training mode."""
        self.context.training_mode = True
        return """
נכנסתי למצב אימון. עכשיו אתה יכול ללמד אותי:
• כתוב עובדה ואני אשמור אותה
• השתמש ב-"למד: <עובדה>" כדי ללמד עובדה ספציפית
• השתמש ב-"ש: <שאלה> ת: <תשובה>" ללימוד שאלות ותשובות
• השתמש ב-"קובץ: <נתיב>" כדי ללמוד מקובץ

כתוב "סיום" כדי לצאת ממצב אימון.
""".strip()

    def _cmd_status(self, args: str) -> str:
        """Show status and statistics."""
        stats = self.trainer.get_training_stats()

        lines = [
            f"סטטיסטיקות מערכת:",
            f"  סה\"כ פריטי ידע: {stats['total_entries']}",
            "",
            "לפי מקור:",
        ]

        for source, count in stats.get("by_source", {}).items():
            lines.append(f"  {source}: {count}")

        lines.append("")
        lines.append("לפי סוג:")

        for doc_type, count in stats.get("by_type", {}).items():
            lines.append(f"  {doc_type}: {count}")

        return "\n".join(lines)

    def _cmd_clear(self, args: str) -> str:
        """Clear conversation history."""
        self.context.clear()
        return "היסטוריית השיחה נוקתה."

    def _cmd_search(self, args: str) -> str:
        """Search knowledge base."""
        if not args:
            return "נא לספק מילת חיפוש. דוגמה: חפש פייתון"

        results = self.kb.search(args, n_results=5)

        if not results:
            return f"לא נמצאו תוצאות עבור: {args}"

        lines = [f"נמצאו {len(results)} תוצאות:"]
        for i, result in enumerate(results, 1):
            score_pct = int(result["score"] * 100)
            content_preview = result["content"][:100]
            if len(result["content"]) > 100:
                content_preview += "..."
            lines.append(f"\n{i}. [{score_pct}%] {content_preview}")

        return "\n".join(lines)

    def _cmd_export(self, args: str) -> str:
        """Export knowledge to JSON file."""
        filepath = args or "knowledge_export.json"
        try:
            self.kb.export_to_json(filepath)
            return f"הידע יוצא בהצלחה לקובץ: {filepath}"
        except Exception as e:
            return f"שגיאה בייצוא: {e}"

    def _cmd_import(self, args: str) -> str:
        """Import knowledge from JSON file."""
        if not args:
            return "נא לספק נתיב לקובץ. דוגמה: ייבוא knowledge.json"

        try:
            count = self.kb.import_from_json(args)
            return f"יובאו {count} פריטי ידע מהקובץ."
        except FileNotFoundError:
            return f"הקובץ לא נמצא: {args}"
        except Exception as e:
            return f"שגיאה בייבוא: {e}"
