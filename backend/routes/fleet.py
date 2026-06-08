from fastapi import APIRouter, HTTPException
from ..database.connection import get_db_connection

router = APIRouter(prefix="/fleet", tags=["Fleet Management"])

@router.get("/status")
def get_fleet_status():
    try:
        conn = get_db_connection()
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
        
        conn.close()
        return {
            "success": True,
            "drivers": drivers,
            "vehicles": vehicles,
            "summary": {
                "valid_drivers": valid_drivers,
                "total_drivers": total_drivers,
                "valid_vehicles": valid_vehicles,
                "total_vehicles": total_vehicles
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
