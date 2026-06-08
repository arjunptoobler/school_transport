"""vector_db.py — ChromaDB client, collection initialisation, and query interface.

Source documents come from rag/documents/ via ingestion.load_documents().
The vector store persists at backend/rag/chroma_db/ (gitignored).
"""

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
import google.generativeai as genai
from ..config import settings
from .ingestion import load_documents


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Production-grade embedding function calling Google's text-embedding-004 model.

    Includes asymmetric routing for query/document matching and a 384-dimensional
    local fallback for offline safety.
    """

    def __init__(self, is_query: bool = False):
        self.is_query = is_query

    def __call__(self, input: Documents) -> Embeddings:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return self._local_fallback(input)

        try:
            genai.configure(api_key=api_key)
            task_type = "retrieval_query" if self.is_query else "retrieval_document"
            response = genai.embed_content(
                model="models/text-embedding-004", contents=input, task_type=task_type
            )
            # Response list of lists
            return response["embedding"]
        except Exception as e:
            print(f"[RAG WARNING] Gemini Embedding API failed: {e}. Falling back to local vectorizer.")
            return self._local_fallback(input)

    def _local_fallback(self, input: Documents) -> Embeddings:
        embeddings = []
        for text in input:
            vector = [0.0] * 384
            for i, c in enumerate(text[:1024]):
                h = (ord(c) * (i + 1)) % 384
                vector[h] += 1.0
            norm = sum(x**2 for x in vector) ** 0.5 or 1.0
            embeddings.append([x / norm for x in vector])
        return embeddings


_chroma_client = None


def _get_client() -> chromadb.PersistentClient:
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
    return _chroma_client


def _get_embedding_fn(is_query: bool = False) -> GeminiEmbeddingFunction:
    return GeminiEmbeddingFunction(is_query=is_query)


def init_vector_db() -> None:
    """Idempotent — loads documents and updates the vector collection.

    Recreates the collection if a schema / embedding size mismatch is detected
    during upgrades.
    """
    client = _get_client()
    ef = _get_embedding_fn(is_query=False)

    collection_name = "adek_regulations"

    # Self-healing migration check for vector size/schema mismatch
    try:
        collection = client.get_collection(name=collection_name, embedding_function=ef)
        # Test a dummy query to verify embedding dimension compatibility
        collection.query(query_texts=["test"], n_results=1)
    except Exception:
        # Delete and recreate if schema is incompatible or collection does not exist
        try:
            client.delete_collection(name=collection_name)
        except Exception:
            pass
        collection = client.create_collection(name=collection_name, embedding_function=ef)

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
    """Semantic search over the ingested policy collection using Gemini text-embedding-004."""
    client = _get_client()
    # Use query-type task embedding logic
    ef = _get_embedding_fn(is_query=True)

    try:
        collection = client.get_collection(name="adek_regulations", embedding_function=ef)
    except Exception:
        init_vector_db()
        collection = client.get_collection(name="adek_regulations", embedding_function=ef)

    results = collection.query(query_texts=[query_text], n_results=n_results)

    retrieved = []
    if results and results["documents"]:
        for text, meta in zip(results["documents"][0], results["metadatas"][0]):
            retrieved.append(
                {
                    "text": text,
                    "authority": meta.get("authority", "Unknown"),
                    "filename": meta.get("filename", ""),
                    "chunk_index": meta.get("chunk_index", 0),
                }
            )
    return retrieved
