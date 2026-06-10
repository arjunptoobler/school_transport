import random
from .connection import get_db_connection

def seed_database():
    conn = get_db_connection()
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
        inspection_status TEXT,
        capacity INTEGER,
        current_occupancy INTEGER
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
        description TEXT,
        status TEXT,
        evidence_url TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_boardings (
        boarding_id TEXT PRIMARY KEY,
        student_id TEXT,
        vehicle_id TEXT,
        event_type TEXT,
        timestamp TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fines (
        fine_id TEXT PRIMARY KEY,
        driver_id TEXT,
        vehicle_id TEXT,
        violation_type TEXT,
        amount REAL,
        authority TEXT,
        timestamp TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compliance_sla (
        sla_id TEXT PRIMARY KEY,
        driver_id TEXT,
        incident_id TEXT,
        assigned_date TEXT,
        deadline_date TEXT,
        status TEXT,
        resolution_date TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS edge_telemetry (
        event_id TEXT PRIMARY KEY,
        vehicle_id TEXT,
        event_type TEXT,
        confidence REAL,
        gforce_x REAL,
        gforce_y REAL,
        gforce_z REAL,
        evidence_url TEXT,
        timestamp TEXT
    )
    """)
    
    # Check if data exists in the fines table (indicates new schema is seeded)
    cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='fines'")
    if cursor.fetchone()[0] > 0:
        cursor.execute("SELECT COUNT(*) FROM fines")
        if cursor.fetchone()[0] > 0:
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='student_boardings'")
            if cursor.fetchone()[0] > 0:
                conn.close()
                return

    # Clear old tables to prevent key constraints on re-seeding
    for tbl in ["drivers", "vehicles", "students", "incidents", "fines", "compliance_sla", "edge_telemetry", "student_boardings"]:
        cursor.execute(f"DELETE FROM {tbl}")

    # Seed Drivers (500 records)
    operators = ["Al Ghazal Transport", "Emirates Transport", "Hafilat School Transportation", "Abu Dhabi Transport"]
    first_names = ["Zayed", "Ahmed", "Mustafa", "Yousef", "Saeed", "Khalid", "Tareq", "Mohammed", "Hamad", "Ali", "John"]
    last_names = ["Al Mansoori", "Al Hashimi", "Mahmoud", "Hassan", "Al Remeithi", "Al Zaabi", "Al Junaibi", "Al Hosani"]
    
    drivers = []
    for i in range(1, 501):
        drv_id = f"DRV-{1000 + i}"
        name = f"{random.choice(first_names)} {random.choice(last_names)}"
        permit = "Valid" if i != 45 else "Suspended"
        medical = "Passed" if i != 45 else "Expired"
        training = "Complete" if i % 15 != 0 else "Pending Refresher"
        op = random.choice(operators)
        drivers.append((drv_id, name, permit, medical, training, op))
        
    cursor.executemany("INSERT INTO drivers VALUES (?,?,?,?,?,?)", drivers)
    
    # Seed Vehicles (250 records)
    vehicles = []
    for i in range(1, 251):
        veh_id = f"AU-BUS-{100 + i}"
        plate = f"AD {random.randint(10000, 99999)}"
        age = random.randint(1, 10)
        gps = "online" if i % 40 != 0 else "offline"
        insp = "valid" if i % 30 != 0 else "failed"
        capacity = random.choice([30, 40, 50])
        current_occ = random.randint(5, capacity - 2)
        vehicles.append((veh_id, plate, age, gps, insp, capacity, current_occ))
        
    cursor.executemany("INSERT INTO vehicles VALUES (?,?,?,?,?,?,?)", vehicles)
    
    # Seed Students (5000 records)
    schools = ["Abu Dhabi International School", "GEMS World Academy Abu Dhabi", "The British School Al Khubairat", "ADEK Model School"]
    students = []
    for i in range(1, 5001):
        stud_id = f"STD-{10000 + i}"
        name = f"Student_{i}"
        school = random.choice(schools)
        route = f"AU-Route-{random.randint(10, 250)}"
        guardian = f"Guardian_{i}"
        behavior = f"Stage {random.randint(1, 3)}"
        students.append((stud_id, name, school, route, guardian, behavior))
        
    cursor.executemany("INSERT INTO students VALUES (?,?,?,?,?,?)", students)
    
    # Seed Incidents (1000 records)
    incidents = []
    incident_types = [
        ("Driver Distraction", "high", "Driver detected looking at phone camera feed."),
        ("Missing Guardian", "med", "Guardian was not present at drop-off location."),
        ("Vehicle Inspection Failure", "med", "Pre-trip safety checklist inspection failed."),
        ("Speed Violation", "high", "Vehicle exceeded school zone speed limit."),
        ("Seatbelt Violation", "med", "Student detected without seatbelt while bus was in motion."),
        ("Minor Delay", "low", "Delay reported due to traffic congestion.")
    ]
    statuses = ["Detected", "Validation", "Notification", "Investigation", "Resolution", "Reporting"]
    
    for i in range(1, 1001):
        inc_id = f"INC-2026-{i:04d}"
        inc_type, severity, desc = random.choice(incident_types)
        drv_id = f"DRV-{1000 + random.randint(1, 500)}"
        veh_id = f"AU-BUS-{100 + random.randint(1, 250)}"
        timestamp = f"2026-06-08T{random.randint(7, 16):02d}:{random.randint(0, 59):02d}:00"
        status = random.choice(statuses)
        
        evidence_urls = [
            "https://storage.adek.gov.ae/evidence/collision_ch23.mp4",
            "https://storage.adek.gov.ae/evidence/distracted_drv_99.jpg",
            "https://storage.adek.gov.ae/evidence/telemetry_hb_02.csv",
            "https://storage.adek.gov.ae/evidence/handover_missing_std44.jpg",
            "None"
        ]
        evidence_url = random.choice(evidence_urls)
        
        incidents.append((inc_id, severity, inc_type, drv_id, veh_id, timestamp, desc, status, evidence_url))
        
    cursor.executemany("INSERT INTO incidents VALUES (?,?,?,?,?,?,?,?,?)", incidents)

    # Seed Student Boardings (RFID card swipes)
    boardings = []
    for i in range(1, 201):
        boarding_id = f"BND-{5000 + i}"
        stud_id = f"STD-{10000 + random.randint(1, 5000)}"
        veh_id = f"AU-BUS-{100 + random.randint(1, 250)}"
        etype = random.choice(["boarding", "alighting"])
        ts = f"2026-06-08T{random.randint(7, 16):02d}:{random.randint(0, 59):02d}:00"
        boardings.append((boarding_id, stud_id, veh_id, etype, ts))
        
    cursor.executemany("INSERT INTO student_boardings VALUES (?,?,?,?,?)", boardings)

    # Seed Fines
    fines = []
    fine_violations = [
        ("Driver Distraction", 5000.0, "DMT"),
        ("Speed Violation", 3000.0, "DMT"),
        ("Seatbelt Violation", 1000.0, "ADEK"),
        ("Pre-trip Inspection Failure", 2000.0, "DMT")
    ]
    for i in range(1, 101):
        fine_id = f"FINE-{2000 + i}"
        drv_id = f"DRV-{1000 + random.randint(1, 500)}"
        veh_id = f"AU-BUS-{100 + random.randint(1, 250)}"
        violation, amount, auth = random.choice(fine_violations)
        ts = f"2026-06-08T{random.randint(7, 16):02d}:{random.randint(0, 59):02d}:00"
        fines.append((fine_id, drv_id, veh_id, violation, amount, auth, ts))
        
    cursor.executemany("INSERT INTO fines VALUES (?,?,?,?,?,?,?)", fines)

    # Seed Compliance SLAs
    slas = []
    for i in range(1, 51):
        sla_id = f"SLA-{3000 + i}"
        drv_id = f"DRV-{1000 + random.randint(1, 500)}"
        inc_id = f"INC-2026-{random.randint(1, 1000):04d}"
        assigned = "2026-06-02T08:00:00"
        deadline = "2026-06-07T08:00:00"
        status = "Pending" if i % 3 != 0 else "Completed"
        res_date = "2026-06-06T14:30:00" if status == "Completed" else None
        slas.append((sla_id, drv_id, inc_id, assigned, deadline, status, res_date))
        
    cursor.executemany("INSERT INTO compliance_sla VALUES (?,?,?,?,?,?,?)", slas)

    # Seed Edge Telemetry Logs
    telemetries = []
    telemetry_types = [
        ("Collision", 0.98, -1.2, 3.4, 0.5, "https://storage.adek.gov.ae/evidence/collision_ch23.mp4"),
        ("Phone_Usage", 0.95, 0.0, 0.0, 1.0, "https://storage.adek.gov.ae/evidence/distracted_drv_99.jpg"),
        ("Harsh_Brake", 0.88, -0.9, -2.1, 0.1, "https://storage.adek.gov.ae/evidence/telemetry_hb_02.csv"),
        ("Missing_Guardian", 0.99, 0.0, 0.0, 0.0, "https://storage.adek.gov.ae/evidence/handover_missing_std44.jpg")
    ]
    for i in range(1, 51):
        evt_id = f"EVT-{4000 + i}"
        veh_id = f"AU-BUS-{100 + random.randint(1, 250)}"
        etype, conf, gx, gy, gz, url = random.choice(telemetry_types)
        ts = f"2026-06-08T{random.randint(7, 16):02d}:{random.randint(0, 59):02d}:00"
        telemetries.append((evt_id, veh_id, etype, conf, gx, gy, gz, url, ts))
        
    cursor.executemany("INSERT INTO edge_telemetry VALUES (?,?,?,?,?,?,?,?,?)", telemetries)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed_database()
    print("Database seeded successfully!")
