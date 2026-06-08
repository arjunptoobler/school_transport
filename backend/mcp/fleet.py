from .base import mcp_registry
from ..database.connection import get_db_connection


@mcp_registry.register_tool(name="mcp_get_vehicle_status")
def get_vehicle_status(vehicle_id: str):
    """Query vehicle coordinates, GPS health, and maintenance check status from active db."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
        row = cursor.fetchone()
        if row:
            return {
                "vehicle_id": row["vehicle_id"],
                "license_plate": row["license_plate"],
                "age": row["age"],
                "gps_status": row["gps_status"],
                "inspection_status": row["inspection_status"],
            }
        return {"error": f"Vehicle {vehicle_id} not found"}
    finally:
        conn.close()


@mcp_registry.register_tool(name="mcp_update_inspection_status")
def update_inspection_status(vehicle_id: str, status: str):
    """Set the physical inspection status of a vehicle to ground or approve."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE vehicles SET inspection_status = ? WHERE vehicle_id = ?", (status, vehicle_id))
        conn.commit()
        return {"success": True, "vehicle_id": vehicle_id, "inspection_status": status}
    finally:
        conn.close()
