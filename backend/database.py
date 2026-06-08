import sqlite3
import random
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "school_transport.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create tables
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS drivers (
        driver_id TEXT PRIMARY KEY,
        name TEXT,
        permit_status TEXT,
        medical_status TEXT,
        training_status TEXT,
        operator TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        vehicle_id TEXT PRIMARY KEY,
        license_plate TEXT,
        age INTEGER,
        gps_status TEXT,
        inspection_status TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id TEXT PRIMARY KEY,
        name TEXT,
        school TEXT,
        route TEXT,
        guardian TEXT,
        behavior_stage TEXT
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        incident_id TEXT PRIMARY KEY,
        severity TEXT,
        type TEXT,
        driver_id TEXT,
        vehicle_id TEXT,
        timestamp TEXT,
        description TEXT
    )
    """)
    
    # Check if data exists already
    cursor.execute("SELECT COUNT(*) FROM drivers")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Populate Drivers (500 records)
    operators = ["Al Ghazal Transport", "Emirates Transport", "Hafilat School Transportation", "Abu Dhabi Transport"]
    first_names = ["Zayed", "Ahmed", "Mustafa", "Yousef", "Saeed", "Khalid", "Tareq", "Mohammed", "Hamad", "Ali", "John", "Michael"]
    last_names = ["Al Mansoori", "Al Hashimi", "Mahmoud", "Hassan", "Al Remeithi", "Al Zaabi", "Al Junaibi", "Al Hosani", "Al Ameri", "Smith", "Jones"]
    
    drivers_data = []
    for i in range(1, 501):
        drv_id = f"DRV-{1000 + i}"
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        permit = "Valid" if i != 45 else "Suspended"
        medical = "Passed" if i != 45 else "Expired"
        training = "Complete" if i % 15 != 0 else "Pending Refresher"
        op = random.choice(operators)
        drivers_data.append((drv_id, name, permit, medical, training, op))
        
    cursor.executemany("INSERT INTO drivers VALUES (?,?,?,?,?,?)", drivers_data)
    
    # Populate Vehicles (250 records)
    vehicles_data = []
    for i in range(1, 251):
        veh_id = f"AU-BUS-{100 + i}"
        plate = f"AD {random.randint(10000, 99999)}"
        age = random.randint(1, 10)
        gps = "online" if i % 40 != 0 else "offline"
        insp = "valid" if i % 30 != 0 else "failed"
        vehicles_data.append((veh_id, plate, age, gps, insp))
        
    cursor.executemany("INSERT INTO vehicles VALUES (?,?,?,?,?)", vehicles_data)
    
    # Populate Students (5000 records)
    schools = ["Abu Dhabi International School", "GEMS World Academy Abu Dhabi", "The British School Al Khubairat", "ADEK Model School"]
    students_data = []
    for i in range(1, 5001):
        stud_id = f"STD-{10000 + i}"
        name = f"Student_{i}"
        school = random.choice(schools)
        route = f"AU-Route-{random.randint(10, 250)}"
        guardian = f"Guardian_{i}"
        behavior = f"Stage {random.randint(1, 3)}"
        students_data.append((stud_id, name, school, route, guardian, behavior))
        
    cursor.executemany("INSERT INTO students VALUES (?,?,?,?,?,?)", students_data)
    
    # Populate Incidents (1000 records)
    incidents_data = []
    incident_types = [
        ("Driver Distraction", "high", "Driver detected looking at phone camera feed."),
        ("Missing Guardian", "med", "Guardian was not present at drop-off location."),
        ("Vehicle Inspection Failure", "med", "Pre-trip safety checklist inspection failed."),
        ("Speed Violation", "high", "Vehicle exceeded school zone speed limit."),
        ("Seatbelt Violation", "med", "Student detected without seatbelt while bus was in motion."),
        ("Minor Delay", "low", "Delay reported due to traffic congestion.")
    ]
    
    for i in range(1, 1001):
        inc_id = f"INC-2026-{880 - i}"
        inc_type, severity, desc = random.choice(incident_types)
        drv_id = f"DRV-{1000 + random.randint(1, 500)}"
        veh_id = f"AU-BUS-{100 + random.randint(1, 250)}"
        timestamp = f"2026-06-08T{random.randint(7, 16):02d}:{random.randint(0, 59):02d}:00"
        incidents_data.append((inc_id, severity, inc_type, drv_id, veh_id, timestamp, desc))
        
    cursor.executemany("INSERT INTO incidents VALUES (?,?,?,?,?,?,?)", incidents_data)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")
