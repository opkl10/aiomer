"""Trainer - Module for training the AI with new knowledge."""

import re
from pathlib import Path
from typing import Optional

from .knowledge_base import KnowledgeBase


class Trainer:
    """Handles training the AI system with new knowledge."""

    def __init__(self, knowledge_base: KnowledgeBase):
        """
        Initialize the trainer.

        Args:
            knowledge_base: The knowledge base to train
        """
        self.kb = knowledge_base

    def train_from_text(
        self,
        text: str,
        source: str = "direct_training",
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> int:
        """
        Train from raw text by chunking and adding to knowledge base.

        Args:
            text: The text to learn from
            source: Source identifier
            chunk_size: Maximum characters per chunk
            overlap: Character overlap between chunks

        Returns:
            Number of chunks added
        """
        chunks = self._chunk_text(text, chunk_size, overlap)

        for i, chunk in enumerate(chunks):
            self.kb.add_knowledge(
                content=chunk,
                source=source,
                metadata={"chunk_index": i, "total_chunks": len(chunks)},
            )

        return len(chunks)

    def train_from_file(self, filepath: str) -> int:
        """
        Train from a file.

        Args:
            filepath: Path to the file

        Returns:
            Number of chunks added
        """
        path = Path(filepath)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        content = path.read_text(encoding="utf-8")

        return self.train_from_text(
            text=content,
            source=f"file:{path.name}",
        )

    def train_from_qa(
        self,
        question: str,
        answer: str,
        topic: Optional[str] = None,
    ) -> str:
        """
        Train from a question-answer pair.

        Args:
            question: The question
            answer: The answer
            topic: Optional topic/category

        Returns:
            The document ID
        """
        # Format as Q&A
        content = f"שאלה: {question}\nתשובה: {answer}"

        metadata = {"type": "qa"}
        if topic:
            metadata["topic"] = topic

        return self.kb.add_knowledge(
            content=content,
            source="qa_training",
            metadata=metadata,
        )

    def train_from_facts(self, facts: list[str], topic: Optional[str] = None) -> int:
        """
        Train from a list of facts.

        Args:
            facts: List of fact statements
            topic: Optional topic/category

        Returns:
            Number of facts added
        """
        count = 0
        for fact in facts:
            fact = fact.strip()
            if fact:
                metadata = {"type": "fact"}
                if topic:
                    metadata["topic"] = topic

                self.kb.add_knowledge(
                    content=fact,
                    source="fact_training",
                    metadata=metadata,
                )
                count += 1

        return count

    def train_interactive(self, user_input: str) -> dict:
        """
        Process interactive training input.

        Supports formats:
        - "למד: <content>" - Learn a fact
        - "ש: <question> ת: <answer>" - Learn Q&A
        - "קובץ: <path>" - Learn from file

        Args:
            user_input: The training input from user

        Returns:
            Dict with status and details
        """
        user_input = user_input.strip()

        # Check for Q&A format
        qa_match = re.match(r"ש:\s*(.+?)\s*ת:\s*(.+)", user_input, re.DOTALL)
        if qa_match:
            question = qa_match.group(1).strip()
            answer = qa_match.group(2).strip()
            doc_id = self.train_from_qa(question, answer)
            return {
                "status": "success",
                "type": "qa",
                "message": f"נלמדה שאלה ותשובה חדשה",
                "doc_id": doc_id,
            }

        # Check for file format
        if user_input.startswith("קובץ:"):
            filepath = user_input[5:].strip()
            try:
                count = self.train_from_file(filepath)
                return {
                    "status": "success",
                    "type": "file",
                    "message": f"נלמדו {count} חלקים מהקובץ",
                    "chunks": count,
                }
            except FileNotFoundError:
                return {
                    "status": "error",
                    "type": "file",
                    "message": f"הקובץ לא נמצא: {filepath}",
                }

        # Check for fact format
        if user_input.startswith("למד:"):
            fact = user_input[4:].strip()
            doc_id = self.kb.add_knowledge(
                content=fact,
                source="interactive_training",
                metadata={"type": "fact"},
            )
            return {
                "status": "success",
                "type": "fact",
                "message": "נלמדה עובדה חדשה",
                "doc_id": doc_id,
            }

        # Default: treat as general knowledge
        doc_id = self.kb.add_knowledge(
            content=user_input,
            source="interactive_training",
        )
        return {
            "status": "success",
            "type": "general",
            "message": "נלמד מידע חדש",
            "doc_id": doc_id,
        }

    def _chunk_text(
        self,
        text: str,
        chunk_size: int = 500,
        overlap: int = 50,
    ) -> list[str]:
        """Split text into overlapping chunks."""
        # Clean text
        text = text.strip()

        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence endings
                for sep in [".", "!", "?", "\n\n", "\n"]:
                    last_sep = text.rfind(sep, start, end)
                    if last_sep > start + chunk_size // 2:
                        end = last_sep + 1
                        break

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - overlap

        return chunks

    def get_training_stats(self) -> dict:
        """Get statistics about the training data."""
        all_docs = self.kb.get_all()

        stats = {
            "total_entries": len(all_docs),
            "by_source": {},
            "by_type": {},
        }

        for doc in all_docs:
            metadata = doc.get("metadata", {})

            # Count by source
            source = metadata.get("source", "unknown")
            stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

            # Count by type
            doc_type = metadata.get("type", "general")
            stats["by_type"][doc_type] = stats["by_type"].get(doc_type, 0) + 1

        return stats
