import logging
from .base import mcp_registry

logger = logging.getLogger(__name__)

@mcp_registry.register_tool(name="mcp_fetch_dashcam_video")
def fetch_dashcam_video(vehicle_id: str, timestamp: str, duration_seconds: int = 15) -> dict:
    """
    Fetches a specific video clip from the bus edge DVR system corresponding to the event timestamp.
    """
    logger.info(f"Fetching {duration_seconds}s dashcam clip for {vehicle_id} at {timestamp}")
    
    # Mocking edge video retrieval
    return {
        "vehicle_id": vehicle_id,
        "clip_url": f"s3://adek-edge-videos/{vehicle_id}/{timestamp}.mp4",
        "status": "Downloaded to Central Storage"
    }

@mcp_registry.register_tool(name="mcp_get_edge_confidence_score")
def get_edge_confidence_score(event_id: str) -> dict:
    """
    Retrieves the raw Edge AI neural network confidence score for a specific detected event (e.g. distraction).
    """
    logger.info(f"Retrieving edge confidence score for event {event_id}")
    
    return {
        "event_id": event_id,
        "model_version": "YOLO-Edge-v4.2",
        "confidence_score": 0.94,
        "bounding_boxes": [{"label": "mobile_phone", "x": 120, "y": 45, "w": 30, "h": 60}]
    }

@mcp_registry.register_tool(name="mcp_attach_evidence_package")
def attach_evidence_package(incident_id: str, media_urls: list, confidence_score: float) -> dict:
    """
    Attaches media clips and AI confidence scores as an immutable evidence package to the official incident ticket.
    """
    logger.info(f"Attaching evidence package to incident {incident_id}")
    
    return {
        "incident_id": incident_id,
        "evidence_package_id": f"EVID-{incident_id}-1",
        "status": "Sealed & Attached"
    }
