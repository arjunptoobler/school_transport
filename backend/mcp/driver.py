from .base import mcp
from ..database.connection import get_db_connection


@mcp.tool(name="mcp_get_driver_record")
def get_driver_record(driver_id: str) -> dict:
    """Retrieve driver licensing compliance, medical validation state, and completed training modules."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM drivers WHERE driver_id = ?", (driver_id,))
        row = cursor.fetchone()
        if row:
            return {
                "driver_id": row["driver_id"],
                "name": row["name"],
                "permit_status": row["permit_status"],
                "medical_status": row["medical_status"],
                "training_status": row["training_status"],
                "operator": row["operator"],
            }
        return {"error": f"Driver {driver_id} not found"}
    finally:
        conn.close()


@mcp.tool(name="mcp_find_available_driver")
def find_available_driver(exclude_driver_id: str, operator: str = "") -> dict:
    """Find a fully compliant replacement driver — valid permit, passed medical, complete training.
    Prefers same operator; falls back to any operator if none available."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if operator:
            cursor.execute(
                "SELECT * FROM drivers WHERE permit_status='Valid' AND medical_status='Passed' "
                "AND training_status='Complete' AND driver_id != ? AND operator = ? LIMIT 1",
                (exclude_driver_id, operator),
            )
            row = cursor.fetchone()
            if row:
                return {"found": True, "driver_id": row["driver_id"], "name": row["name"],
                        "operator": row["operator"], "training_status": row["training_status"]}
        cursor.execute(
            "SELECT * FROM drivers WHERE permit_status='Valid' AND medical_status='Passed' "
            "AND training_status='Complete' AND driver_id != ? LIMIT 1",
            (exclude_driver_id,),
        )
        row = cursor.fetchone()
        if row:
            return {"found": True, "driver_id": row["driver_id"], "name": row["name"],
                    "operator": row["operator"], "training_status": row["training_status"]}
        return {"found": False, "message": "No compliant replacement driver currently available"}
    finally:
        conn.close()


@mcp.tool(name="mcp_assign_replacement_driver")
def assign_replacement_driver(vehicle_id: str, new_driver_id: str, delay_minutes: int = 10) -> dict:
    """Formally assign a replacement driver to a vehicle and update the DB record."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE vehicles SET assigned_driver_id = ? WHERE vehicle_id = ?",
            (new_driver_id, vehicle_id),
        )
        # Fetch the replacement driver's name for the confirmation record
        cursor.execute("SELECT name, operator FROM drivers WHERE driver_id = ?", (new_driver_id,))
        row = cursor.fetchone()
        conn.commit()
        if row:
            return {
                "success": True,
                "vehicle_id": vehicle_id,
                "new_driver_id": new_driver_id,
                "new_driver_name": row["name"],
                "operator": row["operator"],
                "delay_minutes": delay_minutes,
            }
        return {"success": False, "error": f"Driver {new_driver_id} not found"}
    finally:
        conn.close()


@mcp.tool(name="mcp_update_driver_status")
def update_driver_status(driver_id: str, permit_status: str, training_status: str = "") -> dict:
    """Update driver permit clearance or training compliance status."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if training_status:
            cursor.execute(
                "UPDATE drivers SET permit_status = ?, training_status = ? WHERE driver_id = ?",
                (permit_status, training_status, driver_id),
            )
        else:
            cursor.execute("UPDATE drivers SET permit_status = ? WHERE driver_id = ?", (permit_status, driver_id))
        conn.commit()
        return {"success": True, "driver_id": driver_id, "permit_status": permit_status}
    finally:
        conn.close()
