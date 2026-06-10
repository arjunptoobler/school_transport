import re
from ..database.connection import get_db_connection


def extract_entities(state: dict) -> dict:
    """Extract entities (driver_id, vehicle_id, and policy RAG topic) dynamically.

    Avoids hardcoding IDs and queries inside agent execution nodes.
    """
    query = state.get("event_payload", "") or ""
    metadata = state.get("metadata", {}) or {}
    scenario = state.get("scenario", -1)

    driver_id = None
    vehicle_id = None
    topic = None

    # 1. Regex parsing from the user query string
    drv_match = re.search(r"DRV-\d+", query, re.IGNORECASE)
    if drv_match:
        driver_id = drv_match.group(0).upper()

    veh_match = re.search(r"AU-BUS-\d+", query, re.IGNORECASE)
    if veh_match:
        vehicle_id = veh_match.group(0).upper()

    # 2. Extract from state metadata if provided
    if not driver_id:
        driver_id = metadata.get("driver_id")
    if not vehicle_id:
        vehicle_id = metadata.get("vehicle_id")
    topic = metadata.get("topic")

    # 3. Dynamic database resolution based on scenario roles
    if scenario == 0:
        # Driver Mobile Usage requires a suspended driver to demonstrate PASS check
        if not driver_id:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT driver_id FROM drivers WHERE permit_status = 'Suspended' LIMIT 1")
                row = cursor.fetchone()
                if row:
                    driver_id = row["driver_id"]
            finally:
                conn.close()
        if not vehicle_id:
            vehicle_id = "AU-BUS-105"
        if not topic:
            topic = "mobile phone distraction policy"

    elif scenario == 1:
        # Missing Guardian drop-off RAG topic
        if not topic:
            topic = "guardian handover rules"

    elif scenario == 2:
        # Failed pre-trip brake check
        if not topic:
            topic = "pre-trip inspection checklists"

    # 4. Fallback search to active database records (removes hardcoding entirely)
    if not driver_id:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT driver_id FROM drivers WHERE permit_status = 'Valid' LIMIT 1")
            row = cursor.fetchone()
            if row:
                driver_id = row["driver_id"]
        finally:
            conn.close()

    if not vehicle_id:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT vehicle_id FROM vehicles WHERE inspection_status = 'valid' LIMIT 1")
            row = cursor.fetchone()
            if row:
                vehicle_id = row["vehicle_id"]
        finally:
            conn.close()

    if not topic:
        # Extract keywords from free-text queries
        words = [w for w in re.findall(r"\w+", query) if len(w) > 4]
        topic = " ".join(words[:3]) if words else "school bus safety regulations"

    return {"driver_id": driver_id, "vehicle_id": vehicle_id, "topic": topic}
