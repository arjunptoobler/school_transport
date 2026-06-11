import os
import requests
from dotenv import load_dotenv

# Load settings from root .env
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(_PROJECT_ROOT, ".env"))

ORS_API_KEY = os.getenv("ORS_API_KEY", "").strip()

# High-fidelity mock GeoJSON paths in London
# Start: Depot [-0.1500, 51.5030]
# End: School [-0.1220, 51.5120]
# Roadblock: Piccadilly [-0.1420, 51.5070]
MOCK_NORMAL_PATH = [
    [-0.1500, 51.5030],  # Hyde Park Corner (Depot)
    [-0.1460, 51.5055],  # Piccadilly / Down St
    [-0.1420, 51.5070],  # Piccadilly / Green Park
    [-0.1380, 51.5085],  # Piccadilly / St James's
    [-0.1340, 51.5100],  # Piccadilly Circus
    [-0.1280, 51.5105],  # Leicester Square
    [-0.1220, 51.5120]   # Covent Garden (School)
]

MOCK_DETOUR_PATH = [
    [-0.1500, 51.5030],  # Hyde Park Corner (Depot)
    [-0.1508, 51.5058],  # Park Lane
    [-0.1480, 51.5078],  # Curzon St
    [-0.1435, 51.5088],  # Berkeley Square
    [-0.1390, 51.5098],  # Conduit St
    [-0.1340, 51.5100],  # Piccadilly Circus
    [-0.1280, 51.5105],  # Leicester Square
    [-0.1220, 51.5120]   # Covent Garden (School)
]

MOCK_BREAKDOWN_TRANSFER_PATH = [
    [-0.1500, 51.5030],  # Hyde Park Corner (Depot)
    [-0.1460, 51.5055],  # Piccadilly
    [-0.1400, 51.5075],  # Bus 2 breakdown point
    [-0.1340, 51.5100],  # Piccadilly Circus
    [-0.1280, 51.5105],  # Leicester Square
    [-0.1220, 51.5120]   # Covent Garden (School)
]


def calculate_route(start: list, end: list, roadblock: list = None) -> dict:
    """Calculate the route from start [lon, lat] to end [lon, lat].
    
    If roadblock is provided as [lon, lat], ORS will avoid it.
    If ORS_API_KEY is missing, falls back to pre-defined London paths.
    """
    # 1. Try real ORS API if key is present
    if ORS_API_KEY:
        try:
            url = "https://api.openrouteservice.org/v2/directions/driving-car/geojson"
            headers = {
                "Authorization": ORS_API_KEY,
                "Content-Type": "application/json"
            }
            payload = {
                "coordinates": [start, end]
            }
            
            # If a roadblock is active, create a bounding box polygon around it to avoid
            if roadblock:
                lon, lat = roadblock
                # Expand roadblock to a 150m bounding box polygon
                min_lat, max_lat = lat - 0.001, lat + 0.001
                min_lon, max_lon = lon - 0.0015, lon + 0.0015
                
                payload["options"] = {
                    "avoid_polygons": {
                        "type": "Polygon",
                        "coordinates": [[
                            [min_lon, min_lat],
                            [max_lon, min_lat],
                            [max_lon, max_lat],
                            [min_lon, max_lat],
                            [min_lon, min_lat]
                        ]]
                    }
                }
                
            response = requests.post(url, json=payload, headers=headers, timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"ORS API returned error: {response.text}. Falling back to mock data.")
        except Exception as e:
            print(f"ORS API request failed: {e}. Falling back to mock data.")
            
    # 2. Offline Mock Fallback
    # Detect which scenario is running based on inputs
    is_detour = roadblock is not None
    
    # If starting from Depot and ending at School
    if abs(start[0] - (-0.1500)) < 0.01 and abs(end[0] - (-0.1220)) < 0.01:
        if is_detour:
            coords = MOCK_DETOUR_PATH
            distance = 2800.0  # meters
            duration = 420.0   # seconds
        else:
            coords = MOCK_NORMAL_PATH
            distance = 2400.0
            duration = 330.0
    # If routing for breakdown transfer (Starts at Depot, goes to breakdown, then school)
    elif abs(start[0] - (-0.1500)) < 0.01 and abs(start[1] - 51.5030) < 0.01 and is_detour == False:
        coords = MOCK_BREAKDOWN_TRANSFER_PATH
        distance = 2600.0
        duration = 380.0
    else:
        # Default straight-line interpolation if user inputs custom coordinates
        coords = [start, end]
        distance = 3000.0
        duration = 450.0

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "distance": distance,
                    "duration": duration,
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coords
                }
            }
        ]
    }
