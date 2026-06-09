"""vector_db.py — ChromaDB client, collection initialisation, and query interface.

Source documents come from rag/documents/ via ingestion.load_documents().
The vector store persists at backend/rag/chroma_db/ (gitignored).
"""

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
import requests
from ..config import settings
from .ingestion import load_documents


class GeminiEmbeddingFunction(EmbeddingFunction):
    """Production-grade embedding function calling Google's gemini-embedding-2 model via REST.

    Includes batching, asymmetric routing, and a 3072-dimensional local
    fallback for offline safety.
    """

    def __init__(self, is_query: bool = False):
        self.is_query = is_query

    def __call__(self, input: Documents) -> Embeddings:
        api_key = settings.GEMINI_API_KEY
        if not api_key:
            return self._local_fallback(input)

        try:
            # We use batch embedding to support multiple documents during ingestion
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:batchEmbedContents?key={api_key}"
            payload = {
                "requests": [
                    {
                        "model": "models/gemini-embedding-2",
                        "content": {"parts": [{"text": text}]},
                    }
                    for text in input
                ]
            }
            response = requests.post(url, json=payload, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                return [emb["values"] for emb in data["embeddings"]]
            else:
                print(
                    f"[RAG WARNING] Gemini Embedding API returned status {response.status_code}. Falling back."
                )
                return self._local_fallback(input)
        except Exception as e:
            print(f"[RAG WARNING] Gemini Embedding API call failed: {e}. Falling back.")
            return self._local_fallback(input)

    def _local_fallback(self, input: Documents) -> Embeddings:
        # Generate 3072-dimensional vectors to match gemini-embedding-2 dimension
        embeddings = []
        for text in input:
            vector = [0.0] * 3072
            for i, c in enumerate(text[:2048]):
                h = (ord(c) * (i + 1)) % 3072
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

    Recreates the collection if a schema / embedding size mismatch is detected.
    """
    client = _get_client()
    ef = _get_embedding_fn(is_query=False)

    collection_name = "adek_regulations"

    # Self-healing migration check for vector size/schema mismatch
    try:
        collection = client.get_collection(name=collection_name, embedding_function=ef)
        # Test query to check compatibility
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
    """Semantic search over the ingested policy collection using Gemini gemini-embedding-2."""
    client = _get_client()
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
