"""
ingestion.py — Document loader for the RAG pipeline.

Walks rag/documents/<authority>/<filename>.txt (or .pdf when a PDF parser
is added) and returns a flat list of document chunks ready for ChromaDB.

Adding a new source:
  1. Drop a .txt file into rag/documents/<authority>/
  2. Restart the server — init_vector_db() calls load_documents() automatically.
"""

import os
from typing import List, Dict
from ..config import settings


def load_documents() -> List[Dict]:
    """
    Walk RAG_DOCS_PATH and return a list of document dicts:
        { "id": str, "text": str, "metadata": { authority, filename, section } }

    Currently supports .txt files. Extend _parse_file() for PDF support.
    """
    docs = []
    base = settings.RAG_DOCS_PATH

    if not os.path.exists(base):
        return docs

    for authority in os.listdir(base):
        authority_path = os.path.join(base, authority)
        if not os.path.isdir(authority_path):
            continue

        for filename in os.listdir(authority_path):
            filepath = os.path.join(authority_path, filename)
            if not os.path.isfile(filepath):
                continue

            chunks = _parse_file(filepath, authority, filename)
            docs.extend(chunks)

    return docs


def _parse_file(filepath: str, authority: str, filename: str) -> List[Dict]:
    """Split a file into paragraph-level chunks."""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".txt":
        return _chunk_txt(filepath, authority, filename)

    # Future: add .pdf support here via pypdf or pdfminer
    # if ext == ".pdf":
    #     return _chunk_pdf(filepath, authority, filename)

    return []


def _chunk_txt(filepath: str, authority: str, filename: str) -> List[Dict]:
    """Split plain-text file on double newlines (paragraph boundaries)."""
    with open(filepath, "r", encoding="utf-8") as f:
        raw = f.read()

    paragraphs = [p.strip() for p in raw.split("\n\n") if p.strip()]
    chunks = []

    for idx, para in enumerate(paragraphs):
        doc_id = f"{authority}_{os.path.splitext(filename)[0]}_{idx}"
        chunks.append({
            "id": doc_id,
            "text": para,
            "metadata": {
                "authority": authority.upper(),
                "filename": filename,
                "chunk_index": idx,
            },
        })

    return chunks
