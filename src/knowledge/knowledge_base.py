"""Knowledge Base - Vector store for semantic search and knowledge retrieval."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


class KnowledgeBase:
    """Manages knowledge storage and retrieval using vector embeddings."""

    def __init__(self, data_dir: str = "data", collection_name: str = "knowledge"):
        """
        Initialize the knowledge base.

        Args:
            data_dir: Directory to store the vector database
            collection_name: Name of the ChromaDB collection
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialize embedding model
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(
            path=str(self.data_dir / "chromadb"),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def add_knowledge(
        self,
        content: str,
        source: str = "user_input",
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Add new knowledge to the database.

        Args:
            content: The text content to store
            source: Source of the knowledge (e.g., "user_input", "file", "training")
            metadata: Additional metadata to store

        Returns:
            The ID of the added knowledge
        """
        # Generate unique ID
        doc_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        # Prepare metadata
        doc_metadata = {
            "source": source,
            "created_at": datetime.now().isoformat(),
            **(metadata or {}),
        }

        # Generate embedding
        embedding = self.model.encode(content).tolist()

        # Add to collection
        self.collection.add(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[content],
            metadatas=[doc_metadata],
        )

        return doc_id

    def search(
        self,
        query: str,
        n_results: int = 5,
        min_score: float = 0.3,
    ) -> list[dict]:
        """
        Search for relevant knowledge.

        Args:
            query: The search query
            n_results: Maximum number of results to return
            min_score: Minimum similarity score (0-1)

        Returns:
            List of matching documents with scores
        """
        # Generate query embedding
        query_embedding = self.model.encode(query).tolist()

        # Search collection
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

        # Process results
        documents = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                # Convert distance to similarity score (cosine distance)
                distance = results["distances"][0][i]
                score = 1 - distance  # Convert distance to similarity

                if score >= min_score:
                    documents.append(
                        {
                            "content": doc,
                            "score": score,
                            "metadata": results["metadatas"][0][i],
                            "id": results["ids"][0][i],
                        }
                    )

        return documents

    def get_all(self) -> list[dict]:
        """Get all knowledge entries."""
        results = self.collection.get(include=["documents", "metadatas"])

        documents = []
        if results["documents"]:
            for i, doc in enumerate(results["documents"]):
                documents.append(
                    {
                        "content": doc,
                        "metadata": results["metadatas"][i],
                        "id": results["ids"][i],
                    }
                )

        return documents

    def delete(self, doc_id: str) -> bool:
        """Delete a knowledge entry by ID."""
        try:
            self.collection.delete(ids=[doc_id])
            return True
        except Exception:
            return False

    def clear(self) -> None:
        """Clear all knowledge from the database."""
        # Delete and recreate collection
        self.client.delete_collection(self.collection.name)
        self.collection = self.client.get_or_create_collection(
            name=self.collection.name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        """Get the number of knowledge entries."""
        return self.collection.count()

    def export_to_json(self, filepath: str) -> None:
        """Export all knowledge to a JSON file."""
        documents = self.get_all()
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(documents, f, ensure_ascii=False, indent=2)

    def import_from_json(self, filepath: str) -> int:
        """
        Import knowledge from a JSON file.

        Returns:
            Number of documents imported
        """
        with open(filepath, encoding="utf-8") as f:
            documents = json.load(f)

        count = 0
        for doc in documents:
            content = doc.get("content", "")
            metadata = doc.get("metadata", {})
            if content:
                self.add_knowledge(content, source="json_import", metadata=metadata)
                count += 1

        return count
