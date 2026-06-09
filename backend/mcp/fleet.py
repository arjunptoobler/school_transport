from .base import mcp_registry
from ..database.connection import get_db_connection


@mcp_registry.register_tool(name="mcp_get_vehicle_status")
def get_vehicle_status(vehicle_id: str):
    """Query vehicle coordinates, GPS health, capacity, occupancy, and maintenance check status from active db."""
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
                "capacity": row["capacity"],
                "current_occupancy": row["current_occupancy"],
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


@mcp_registry.register_tool(name="mcp_log_student_boarding")
def log_student_boarding(student_id: str, vehicle_id: str, event_type: str):
    """Log RFID boarding or alighting card swipe. Increments or decrements active bus occupancy."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT capacity, current_occupancy FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
        veh = cursor.fetchone()
        if not veh:
            return {"error": f"Vehicle {vehicle_id} not found"}
            
        capacity = veh["capacity"] or 40
        occupancy = veh["current_occupancy"] or 0
        
        if event_type == "boarding":
            new_occ = min(capacity, occupancy + 1)
        elif event_type == "alighting":
            new_occ = max(0, occupancy - 1)
        else:
            return {"error": f"Invalid event type: {event_type}"}
            
        import datetime
        bnd_id = f"BND-{datetime.datetime.now().strftime('%Y%m%d%H%M%S%f')[:18]}"
        ts = datetime.datetime.now().isoformat()
        cursor.execute("INSERT INTO student_boardings VALUES (?,?,?,?,?)", (bnd_id, student_id, vehicle_id, event_type, ts))
        
        cursor.execute("UPDATE vehicles SET current_occupancy = ? WHERE vehicle_id = ?", (new_occ, vehicle_id))
        conn.commit()
        
        return {
            "success": True,
            "boarding_id": bnd_id,
            "student_id": student_id,
            "vehicle_id": vehicle_id,
            "event_type": event_type,
            "new_occupancy": new_occ,
            "capacity": capacity,
            "utilization": (new_occ / capacity) * 100 if capacity else 0
        }
    finally:
        conn.close()
