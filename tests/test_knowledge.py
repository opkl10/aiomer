"""Tests for knowledge base and trainer modules."""

import json
import tempfile
from pathlib import Path

import pytest

from src.knowledge import KnowledgeBase, Trainer


class TestKnowledgeBase:
    """Tests for KnowledgeBase class."""

    @pytest.fixture
    def kb(self, tmp_path):
        """Create a temporary knowledge base."""
        return KnowledgeBase(data_dir=str(tmp_path), collection_name="test_kb")

    def test_add_and_search(self, kb):
        """Test adding knowledge and searching for it."""
        # Add knowledge
        doc_id = kb.add_knowledge(
            content="Python is a programming language",
            source="test",
        )
        assert doc_id is not None

        # Search for it
        results = kb.search("What is Python?")
        assert len(results) > 0
        assert "Python" in results[0]["content"]

    def test_count(self, kb):
        """Test counting entries."""
        assert kb.count() == 0

        kb.add_knowledge("First fact")
        assert kb.count() == 1

        kb.add_knowledge("Second fact")
        assert kb.count() == 2

    def test_delete(self, kb):
        """Test deleting knowledge."""
        doc_id = kb.add_knowledge("Temporary knowledge")
        assert kb.count() == 1

        result = kb.delete(doc_id)
        assert result is True
        assert kb.count() == 0

    def test_clear(self, kb):
        """Test clearing all knowledge."""
        kb.add_knowledge("Fact 1")
        kb.add_knowledge("Fact 2")
        kb.add_knowledge("Fact 3")
        assert kb.count() == 3

        kb.clear()
        assert kb.count() == 0

    def test_export_import_json(self, kb, tmp_path):
        """Test exporting and importing JSON."""
        # Add some knowledge
        kb.add_knowledge("First fact about AI")
        kb.add_knowledge("Second fact about machine learning")

        # Export
        export_path = tmp_path / "export.json"
        kb.export_to_json(str(export_path))

        assert export_path.exists()
        with open(export_path) as f:
            data = json.load(f)
        assert len(data) == 2

        # Create new KB and import
        kb2 = KnowledgeBase(data_dir=str(tmp_path / "kb2"), collection_name="test_kb2")
        count = kb2.import_from_json(str(export_path))
        assert count == 2
        assert kb2.count() == 2


class TestTrainer:
    """Tests for Trainer class."""

    @pytest.fixture
    def trainer(self, tmp_path):
        """Create a trainer with temporary knowledge base."""
        kb = KnowledgeBase(data_dir=str(tmp_path), collection_name="test_trainer")
        return Trainer(kb)

    def test_train_from_text(self, trainer):
        """Test training from raw text."""
        text = "This is a test. " * 50  # Long enough to be chunked
        count = trainer.train_from_text(text, chunk_size=100)
        assert count > 0

    def test_train_from_qa(self, trainer):
        """Test training from Q&A pair."""
        doc_id = trainer.train_from_qa(
            question="What is Python?",
            answer="A programming language",
            topic="programming",
        )
        assert doc_id is not None

        # Verify it was added
        results = trainer.kb.search("What is Python?")
        assert len(results) > 0

    def test_train_from_facts(self, trainer):
        """Test training from fact list."""
        facts = [
            "The sun is a star",
            "Water boils at 100 degrees Celsius",
            "Python was created by Guido van Rossum",
        ]
        count = trainer.train_from_facts(facts, topic="science")
        assert count == 3

    def test_train_interactive_fact(self, trainer):
        """Test interactive training with fact format."""
        result = trainer.train_interactive("למד: Python is awesome")
        assert result["status"] == "success"
        assert result["type"] == "fact"

    def test_train_interactive_qa(self, trainer):
        """Test interactive training with Q&A format."""
        result = trainer.train_interactive("ש: מה זה Python? ת: שפת תכנות")
        assert result["status"] == "success"
        assert result["type"] == "qa"

    def test_train_interactive_file_not_found(self, trainer):
        """Test interactive training with non-existent file."""
        result = trainer.train_interactive("קובץ: /nonexistent/file.txt")
        assert result["status"] == "error"
        assert result["type"] == "file"

    def test_get_training_stats(self, trainer):
        """Test getting training statistics."""
        trainer.train_from_qa("Q1", "A1")
        trainer.train_from_facts(["Fact 1", "Fact 2"])

        stats = trainer.get_training_stats()
        assert stats["total_entries"] == 3
        assert "qa_training" in stats["by_source"]
        assert "fact_training" in stats["by_source"]
