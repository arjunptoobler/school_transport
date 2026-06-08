from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..rag.vector_db import query_policy

router = APIRouter(prefix="/policy", tags=["Regulatory Compliance RAG"])

class RAGQuery(BaseModel):
    query: str

@router.post("/query")
def query_policy_endpoint(req: RAGQuery):
    try:
        results = query_policy(req.query)
        return {"success": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
