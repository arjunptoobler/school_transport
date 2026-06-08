# RAG Documents

This folder contains source documents that are chunked and ingested into the
ChromaDB vector store at startup via `backend/rag/ingestion.py`.

## Folder Structure

```
rag/
└── documents/
    ├── adek/          ← ADEK policy PDFs / txt exports
    └── mobility/      ← Abu Dhabi Mobility regulation PDFs / txt exports
```

## Adding Documents

1. Drop `.txt` or `.pdf` files into the appropriate subfolder.
2. Restart the backend — `init_vector_db()` calls `load_documents()` which
   walks this tree and ingests any file not already in the collection.

## Runtime Data

The ChromaDB vector index is stored at `backend/rag/chroma_db/` (gitignored).
It is regenerated automatically from these source files on a clean run.
