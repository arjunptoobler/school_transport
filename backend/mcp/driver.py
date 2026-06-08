from .base import mcp_registry
from ..database.connection import get_db_connection

@mcp_registry.register_tool(name="mcp_get_driver_record")
def get_driver_record(driver_id: str):
    """Retrieve driver licensing compliance, medical validation state, and completed training modules."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM drivers WHERE driver_id = ?", (driver_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "driver_id": row["driver_id"],
            "name": row["name"],
            "permit_status": row["permit_status"],
            "medical_status": row["medical_status"],
            "training_status": row["training_status"],
            "operator": row["operator"]
        }
    return {"error": f"Driver {driver_id} not found"}

@mcp_registry.register_tool(name="mcp_update_driver_status")
def update_driver_status(driver_id: str, permit_status: str, training_status: str = None):
    """Update driver permit clearance or training compliance status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if training_status:
        cursor.execute("UPDATE drivers SET permit_status = ?, training_status = ? WHERE driver_id = ?", 
                       (permit_status, training_status, driver_id))
    else:
        cursor.execute("UPDATE drivers SET permit_status = ? WHERE driver_id = ?", 
                       (permit_status, driver_id))
    conn.commit()
    conn.close()
    return {"success": True, "driver_id": driver_id, "permit_status": permit_status}
