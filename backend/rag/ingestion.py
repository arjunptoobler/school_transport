import os
from typing import Dict, List
from pypdf import PdfReader
from ..config import settings


def load_documents() -> List[Dict]:
    """Walk RAG_DOCS_PATH and return a list of chunked document dicts:

        { "id": str, "text": str, "metadata": { authority, filename, chunk_index } }

    Natively supports both .txt and .pdf documents in the rag/documents folders.
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
    """Route file by extension to the appropriate parser/chunker."""
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".txt":
        return _parse_txt(filepath, authority, filename)
    elif ext == ".pdf":
        return _parse_pdf(filepath, authority, filename)

    return []


def _parse_txt(filepath: str, authority: str, filename: str) -> List[Dict]:
    """Read a text file and split it into semantic chunks."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    return _split_text(content, authority, filename)


def _parse_pdf(filepath: str, authority: str, filename: str) -> List[Dict]:
    """Read a PDF file, extract pages, and split into semantic chunks."""
    try:
        reader = PdfReader(filepath)
        pages_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages_text.append(text)
        content = "\n".join(pages_text)
        return _split_text(content, authority, filename)
    except Exception as e:
        print(f"Error parsing PDF file {filepath}: {e}")
        return []


def _split_text(
    text: str, authority: str, filename: str, chunk_size: int = 600, overlap: int = 120
) -> List[Dict]:
    """Split text recursively with character overlap (Recursive Character Splitting).

    Preserves paragraph and sentence boundaries wherever possible.
    """
    chunks = []
    text_len = len(text)
    start = 0

    idx = 0
    while start < text_len:
        end = min(start + chunk_size, text_len)

        # Try to find a natural boundary near the end of the chunk (paragraph or sentence)
        if end < text_len:
            # Look for double newline first
            boundary = text.rfind("\n\n", start + 200, end)
            if boundary == -1:
                # Look for single newline
                boundary = text.rfind("\n", start + 200, end)
            if boundary == -1:
                # Look for period/sentence boundary
                boundary = text.rfind(". ", start + 200, end)

            if boundary != -1:
                end = boundary + 1

        chunk_text = text[start:end].strip()
        if len(chunk_text) > 30:  # Ignore fragments that are too short to be semantically useful
            doc_id = f"{authority}_{os.path.splitext(filename)[0]}_{idx}"
            chunks.append(
                {
                    "id": doc_id,
                    "text": chunk_text,
                    "metadata": {
                        "authority": authority.upper(),
                        "filename": filename,
                        "chunk_index": idx,
                    },
                }
            )
            idx += 1

        # Advance start index accounting for overlap
        start = end - overlap
        if start >= text_len or (end == text_len):
            break

    return chunks
