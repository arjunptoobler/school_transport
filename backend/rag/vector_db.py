"""
vector_db.py — ChromaDB client, collection initialisation, and query interface.

Source documents come from rag/documents/ via ingestion.load_documents().
The vector store persists at backend/rag/chroma_db/ (gitignored).
"""

import chromadb
from chromadb import EmbeddingFunction
from ..config import settings
from .ingestion import load_documents


class SimpleCharEmbedding(EmbeddingFunction):
    """
    Lightweight character-frequency embedding for demo / offline use.

    Replace with OpenAIEmbeddingFunction or SentenceTransformerEmbeddingFunction
    for production-quality semantic search (see README.md — Scaling section).
    """
    def __call__(self, input):
        embeddings = []
        for text in input:
            vector = [0.0] * 128
            for c in text[:512]:
                vector[ord(c) % 128] += 1.0
            norm = sum(x ** 2 for x in vector) ** 0.5 or 1.0
            embeddings.append([x / norm for x in vector])
        return embeddings


def _get_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)


def _get_embedding_fn() -> SimpleCharEmbedding:
    return SimpleCharEmbedding()


def init_vector_db() -> None:
    """
    Idempotent — loads documents from rag/documents/ and adds any that are
    not already present in the collection (matched by document ID).
    Called automatically by FastAPI lifespan on server start.
    """
    client = _get_client()
    ef = _get_embedding_fn()

    collection = client.get_or_create_collection(
        name="adek_regulations",
        embedding_function=ef,
    )

    existing_ids = set(collection.get()["ids"])
    docs = load_documents()

    new_docs = [d for d in docs if d["id"] not in existing_ids]
    if not new_docs:
        return

    collection.add(
        documents=[d["text"] for d in new_docs],
        metadatas=[d["metadata"] for d in new_docs],
        ids=[d["id"] for d in new_docs],
    )


def query_policy(query_text: str, n_results: int = 3) -> list:
    """Semantic search over the ingested policy collection."""
    client = _get_client()
    ef = _get_embedding_fn()

    collection = client.get_or_create_collection(
        name="adek_regulations",
        embedding_function=ef,
    )

    results = collection.query(query_texts=[query_text], n_results=n_results)

    retrieved = []
    if results and results["documents"]:
        for text, meta in zip(results["documents"][0], results["metadatas"][0]):
            retrieved.append({
                "text": text,
                "authority": meta.get("authority", "Unknown"),
                "filename": meta.get("filename", ""),
                "chunk_index": meta.get("chunk_index", 0),
            })
    return retrieved
