from fastapi import APIRouter, HTTPException
from ..database.connection import get_db_connection

router = APIRouter(prefix="/fleet", tags=["Fleet Management"])


@router.get("/status")
def get_fleet_status():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Query 20 Drivers
        cursor.execute("SELECT * FROM drivers LIMIT 20")
        drivers = [dict(r) for r in cursor.fetchall()]

        # Query 20 Vehicles
        cursor.execute("SELECT * FROM vehicles LIMIT 20")
        vehicles = [dict(r) for r in cursor.fetchall()]

        # Summary counts
        cursor.execute("SELECT COUNT(*) FROM drivers WHERE permit_status = 'Valid'")
        valid_drivers = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM drivers")
        total_drivers = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE inspection_status = 'valid'")
        valid_vehicles = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        total_vehicles = cursor.fetchone()[0]

        return {
            "success": True,
            "drivers": drivers,
            "vehicles": vehicles,
            "summary": {
                "valid_drivers": valid_drivers,
                "total_drivers": total_drivers,
                "valid_vehicles": valid_vehicles,
                "total_vehicles": total_vehicles,
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/kpis")
def get_live_kpis():
    """Compute real-time KPI metrics from the database for the Command Center dashboard."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE gps_status = 'online'")
        active_buses = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM vehicles")
        total_buses = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM drivers WHERE permit_status = 'Valid' AND training_status = 'Complete'")
        compliant_drivers = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM drivers")
        total_drivers = cursor.fetchone()[0]
        compliance_score = round((compliant_drivers / total_drivers) * 100, 1) if total_drivers else 0

        cursor.execute("SELECT COUNT(*) FROM incidents WHERE status NOT IN ('Resolved', 'Resolution', 'Reporting')")
        open_incidents = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'high' AND status NOT IN ('Resolved', 'Resolution', 'Reporting')")
        high_incidents = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE severity = 'med' AND status NOT IN ('Resolved', 'Resolution', 'Reporting')")
        med_incidents = cursor.fetchone()[0]

        # Escalated/Human Review: status = 'Manual Override'
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE status = 'Manual Override'")
        manual_overrides = cursor.fetchone()[0]

        # Auto-resolved: status = 'Resolved'
        cursor.execute("SELECT COUNT(*) FROM incidents WHERE status = 'Resolved'")
        resolved_incidents = cursor.fetchone()[0]

        cursor.execute("SELECT SUM(current_occupancy) FROM vehicles")
        total_students = cursor.fetchone()[0] or 0

        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE gps_status = 'online'")
        gps_active = cursor.fetchone()[0]
        gps_pct = round((gps_active / total_buses) * 100) if total_buses else 0

        cursor.execute("SELECT COUNT(*) FROM vehicles WHERE inspection_status = 'valid'")
        insp_valid = cursor.fetchone()[0]
        insp_pct = round((insp_valid / total_buses) * 100) if total_buses else 0

        return {
            "active_buses": active_buses,
            "total_buses": total_buses,
            "compliance_score": compliance_score,
            "open_incidents": open_incidents,
            "high_incidents": high_incidents,
            "med_incidents": med_incidents,
            "manual_overrides": manual_overrides,
            "resolved_incidents": resolved_incidents,
            "students_in_transit": total_students,
            "gps_active_pct": gps_pct,
            "inspection_valid_pct": insp_pct,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/fines")
def get_recent_fines():
    """Return the 10 most recent fine tickets."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM fines ORDER BY timestamp DESC LIMIT 10")
        return [dict(r) for r in cursor.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/slas")
def get_active_slas():
    """Return active (non-completed) compliance SLA deadlines."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM compliance_sla WHERE status = 'Pending' ORDER BY deadline_date ASC LIMIT 10")
        return [dict(r) for r in cursor.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@router.get("/boardings")
def get_recent_boardings():
    """Return the 15 most recent student RFID boarding/alighting events."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM student_boardings ORDER BY timestamp DESC LIMIT 15")
        return [dict(r) for r in cursor.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()
