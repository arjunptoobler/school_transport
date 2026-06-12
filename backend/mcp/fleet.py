from .base import mcp
from ..database.connection import get_db_connection


@mcp.tool(name="mcp_get_vehicle_status")
def get_vehicle_status(vehicle_id: str) -> dict:
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


@mcp.tool(name="mcp_update_inspection_status")
def update_inspection_status(vehicle_id: str, status: str) -> dict:
    """Set the physical inspection status of a vehicle to ground or approve."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE vehicles SET inspection_status = ? WHERE vehicle_id = ?", (status, vehicle_id))
        conn.commit()
        return {"success": True, "vehicle_id": vehicle_id, "inspection_status": status}
    finally:
        conn.close()


@mcp.tool(name="mcp_log_student_boarding")
def log_student_boarding(student_id: str, vehicle_id: str, event_type: str) -> dict:
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
            "utilization": (new_occ / capacity) * 100 if capacity else 0,
        }
    finally:
        conn.close()


@mcp.tool(name="mcp_optimize_route")
def optimize_route(vehicle_id: str, roadblock_id: str = "") -> dict:
    """Calculate the optimized detour route avoiding any roadblocks, or dispatch a standby bus if grounded."""
    from ..routing_solver import calculate_route
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM vehicles WHERE vehicle_id = ?", (vehicle_id,))
        vehicle = cursor.fetchone()
        if not vehicle:
            return {"error": f"Vehicle {vehicle_id} not found"}

        start_coords = [vehicle["current_lon"] or -0.1500, vehicle["current_lat"] or 51.5030]
        end_coords = [-0.1220, 51.5120]

        rb_coords = None
        if roadblock_id:
            cursor.execute("SELECT * FROM roadblocks WHERE roadblock_id = ?", (roadblock_id,))
            rb = cursor.fetchone()
            if rb:
                rb_coords = [rb["lon"], rb["lat"]]

        route_geojson = calculate_route(start_coords, end_coords, rb_coords)
        props = route_geojson["features"][0]["properties"]
        if "summary" in props:
            distance_km = round(props["summary"]["distance"] / 1000.0, 2)
            duration_mins = round(props["summary"]["duration"] / 60.0, 1)
        else:
            distance_km = round(props["distance"] / 1000.0, 2)
            duration_mins = round(props["duration"] / 60.0, 1)

        if vehicle["inspection_status"] == "failed" or vehicle_id == "AU-BUS-104":
            cursor.execute(
                "SELECT * FROM vehicles WHERE inspection_status = 'valid' AND assigned_route = 'Standby' AND capacity >= ? LIMIT 1",
                (vehicle["current_occupancy"] or 12,),
            )
            standby = cursor.fetchone()
            if standby:
                standby_id = standby["vehicle_id"]
                cursor.execute(
                    "UPDATE vehicles SET current_occupancy = ?, assigned_route = ?, inspection_status = 'valid' WHERE vehicle_id = ?",
                    (vehicle["current_occupancy"], vehicle["assigned_route"], standby_id),
                )
                cursor.execute("UPDATE vehicles SET current_occupancy = 0 WHERE vehicle_id = ?", (vehicle_id,))
                conn.commit()
                standby_start = [standby["current_lon"], standby["current_lat"]]
                standby_route = calculate_route(standby_start, end_coords)
                props_sb = standby_route["features"][0]["properties"]
                if "summary" in props_sb:
                    sb_dist = round(props_sb["summary"]["distance"] / 1000.0, 2)
                    sb_dur = round(props_sb["summary"]["duration"] / 60.0, 1)
                else:
                    sb_dist = round(props_sb["distance"] / 1000.0, 2)
                    sb_dur = round(props_sb["duration"] / 60.0, 1)
                return {
                    "action": "standby_dispatch",
                    "grounded_vehicle": vehicle_id,
                    "dispatched_vehicle": standby_id,
                    "students_transferred": vehicle["current_occupancy"],
                    "distance_km": sb_dist,
                    "duration_mins": sb_dur,
                    "message": f"Bus {vehicle_id} grounded. Standby bus {standby_id} dispatched from Depot.",
                }

        return {
            "action": "roadblock_detour" if roadblock_id else "normal_routing",
            "vehicle_id": vehicle_id,
            "distance_km": distance_km,
            "duration_mins": duration_mins,
            "message": f"Optimized routing active for {vehicle_id}. Distance: {distance_km} km, Duration: {duration_mins} mins.",
        }
    finally:
        conn.close()
