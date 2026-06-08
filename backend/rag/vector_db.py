import os
import chromadb
from chromadb import EmbeddingFunction
from ..config import settings

# Standard embedding function using custom logic conforming to ChromaDB EmbeddingFunction protocol
class SimpleCharEmbedding(EmbeddingFunction):
    def __call__(self, input):
        embeddings = []
        for text in input:
            vector = [0.0] * 128
            for i, c in enumerate(text[:256]):
                dim = ord(c) % 128
                vector[dim] += 1.0
            norm = sum(x**2 for x in vector)**0.5 or 1.0
            vector = [x/norm for x in vector]
            embeddings.append(vector)
        return embeddings

def get_chroma_client():
    return chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)

def init_vector_db():
    client = get_chroma_client()
    embedding_function = SimpleCharEmbedding()
    
    collection = client.get_or_create_collection(
        name="adek_regulations",
        embedding_function=embedding_function
    )
    
    if collection.count() > 0:
        return
        
    documents = [
        {
            "id": "adek_1",
            "text": "ADEK Student Transportation Policy Regulation 14.2: Guardian Handover. Student under Grade 3 / Age 9 must never be left unattended at a drop-off point. If an authorized guardian is not present, the driver or school bus supervisor must retain the student on board, notify school dispatch, and return the student safely to the school campus or local security precinct.",
            "metadata": {"authority": "ADEK", "document": "Transportation Policy", "section": "14.2 Guardian Handover"}
        },
        {
            "id": "adek_2",
            "text": "ADEK Student Protection Policy Sec 4: Incident reporting and supervisor duties. Any safety hazard, student behavior stage escalation, or missing supervisor incident must be logged in the electronic system within 30 minutes of occurrence. Parent notifications must be sent immediately via registered contact channels.",
            "metadata": {"authority": "ADEK", "document": "Student Protection", "section": "4 Incident Reporting"}
        },
        {
            "id": "mob_1",
            "text": "Abu Dhabi Mobility School Transport Rules Sec 2.1: Driver mobile phone usage and distraction. Operating a school transport vehicle while holding or viewing a mobile phone or electronic device is strictly prohibited. It carries a fine of AED 5,000, 24 black points, and immediate suspension of the school bus transport permit.",
            "metadata": {"authority": "Abu Dhabi Mobility", "document": "School Transport Rules", "section": "2.1 Driver Distraction"}
        },
        {
            "id": "mob_2",
            "text": "Abu Dhabi Mobility Vehicle Inspection Checklist: All school transport vehicles must pass a pre-trip and weekly vehicle health check. Crucial items including air conditioning (HVAC) functionality, braking systems pressure thresholds, safety camera operations, and emergency exit release must be fully operational. Failures result in immediate grounding.",
            "metadata": {"authority": "Abu Dhabi Mobility", "document": "Vehicle Checklist", "section": "Weekly Inspection"}
        }
    ]
    
    collection.add(
        documents=[doc["text"] for doc in documents],
        metadatas=[doc["metadata"] for doc in documents],
        ids=[doc["id"] for doc in documents]
    )

def query_policy(query_text: str):
    client = get_chroma_client()
    embedding_function = SimpleCharEmbedding()
    collection = client.get_collection(
        name="adek_regulations",
        embedding_function=embedding_function
    )
    
    results = collection.query(
        query_texts=[query_text],
        n_results=2
    )
    
    retrieved = []
    if results and results["documents"]:
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            retrieved.append({
                "text": doc,
                "authority": meta.get("authority", "Unknown"),
                "document": meta.get("document", "Unknown"),
                "section": meta.get("section", "Unknown")
            })
    return retrieved
