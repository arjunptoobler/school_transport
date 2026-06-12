import random
from .connection import get_db_connection


def seed_database():
    conn = get_db_connection()
    cursor = conn.cursor()

    # ── Schema ────────────────────────────────────────────────────────────

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS operators (
        operator_id   TEXT PRIMARY KEY,
        name          TEXT,
        license_no    TEXT,
        contact_email TEXT,
        contact_phone TEXT,
        hq_location   TEXT
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS drivers (
        driver_id      TEXT PRIMARY KEY,
        name           TEXT,
        permit_status  TEXT,
        medical_status TEXT,
        training_status TEXT,
        operator       TEXT,
        operator_id    TEXT REFERENCES operators(operator_id)
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS vehicles (
        vehicle_id         TEXT PRIMARY KEY,
        license_plate      TEXT,
        age                INTEGER,
        gps_status         TEXT,
        inspection_status  TEXT,
        capacity           INTEGER,
        current_occupancy  INTEGER,
        current_lat        REAL,
        current_lon        REAL,
        assigned_route     TEXT,
        assigned_driver_id TEXT REFERENCES drivers(driver_id)
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roadblocks (
        roadblock_id TEXT PRIMARY KEY,
        lat          REAL,
        lon          REAL,
        radius       REAL,
        description  TEXT
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS parents (
        parent_id    TEXT PRIMARY KEY,
        name         TEXT,
        phone        TEXT,
        email        TEXT,
        relationship TEXT
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        student_id          TEXT PRIMARY KEY,
        name                TEXT,
        school              TEXT,
        route               TEXT,
        guardian            TEXT,
        behavior_stage      TEXT,
        parent_id           TEXT REFERENCES parents(parent_id),
        assigned_vehicle_id TEXT REFERENCES vehicles(vehicle_id)
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incidents (
        incident_id  TEXT PRIMARY KEY,
        severity     TEXT,
        type         TEXT,
        driver_id    TEXT REFERENCES drivers(driver_id),
        vehicle_id   TEXT REFERENCES vehicles(vehicle_id),
        timestamp    TEXT,
        description  TEXT,
        status       TEXT,
        evidence_url TEXT
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS student_boardings (
        boarding_id TEXT PRIMARY KEY,
        student_id  TEXT REFERENCES students(student_id),
        vehicle_id  TEXT REFERENCES vehicles(vehicle_id),
        event_type  TEXT,
        timestamp   TEXT
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fines (
        fine_id        TEXT PRIMARY KEY,
        driver_id      TEXT REFERENCES drivers(driver_id),
        vehicle_id     TEXT REFERENCES vehicles(vehicle_id),
        violation_type TEXT,
        amount         REAL,
        authority      TEXT,
        timestamp      TEXT
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS compliance_sla (
        sla_id          TEXT PRIMARY KEY,
        driver_id       TEXT REFERENCES drivers(driver_id),
        incident_id     TEXT REFERENCES incidents(incident_id),
        assigned_date   TEXT,
        deadline_date   TEXT,
        status          TEXT,
        resolution_date TEXT
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS edge_telemetry (
        event_id   TEXT PRIMARY KEY,
        vehicle_id TEXT REFERENCES vehicles(vehicle_id),
        event_type TEXT,
        confidence REAL,
        gforce_x   REAL,
        gforce_y   REAL,
        gforce_z   REAL,
        evidence_url TEXT,
        timestamp  TEXT
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS incident_audit_log (
        log_id      TEXT PRIMARY KEY,
        incident_id TEXT,
        agent       TEXT,
        action      TEXT,
        detail      TEXT,
        timestamp   TEXT
    )""")

    # ── Skip if already seeded ────────────────────────────────────────────
    cursor.execute("SELECT COUNT(*) FROM operators")
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    random.seed(42)

    # ── OPERATORS (4) ─────────────────────────────────────────────────────
    operators_data = [
        ("OP-001", "Al Ghazal Transport",          "TRN-AG-2021-001", "ops@alghazal.ae",      "+971-2-555-0101", "Abu Dhabi"),
        ("OP-002", "Emirates Transport",            "TRN-ET-2018-002", "ops@emiratestrans.ae", "+971-2-555-0202", "Dubai"),
        ("OP-003", "Hafilat School Transportation", "TRN-HF-2019-003", "ops@hafilat.ae",      "+971-2-555-0303", "Abu Dhabi"),
        ("OP-004", "Abu Dhabi Transport",           "TRN-AD-2015-004", "ops@adtransport.ae",  "+971-2-555-0404", "Abu Dhabi"),
    ]
    cursor.executemany("INSERT INTO operators VALUES (?,?,?,?,?,?)", operators_data)

    # ── DRIVERS (50) ──────────────────────────────────────────────────────
    op_pool = [
        ("OP-001", "Al Ghazal Transport"),
        ("OP-002", "Emirates Transport"),
        ("OP-003", "Hafilat School Transportation"),
        ("OP-004", "Abu Dhabi Transport"),
    ]
    first_names = ["Zayed", "Ahmed", "Mustafa", "Yousef", "Saeed", "Khalid", "Tareq",
                   "Mohammed", "Hamad", "Ali", "Omar", "Rashid", "Faisal", "Sultan"]
    last_names  = ["Al Mansoori", "Al Hashimi", "Mahmoud", "Hassan", "Al Remeithi",
                   "Al Zaabi", "Al Junaibi", "Al Hosani", "Al Marzouqi", "Al Kaabi"]

    drivers_data = []
    for i in range(1, 51):
        drv_id  = f"DRV-{1000 + i}"
        op_id, operator = op_pool[i % 4]
        name = f"{random.choice(first_names)} {random.choice(last_names)}"

        # Demo-specific non-compliant drivers
        if drv_id == "DRV-1004":
            permit, medical, training = "Suspended", "Passed", "Complete"
        elif drv_id == "DRV-1015":
            permit, medical, training = "Suspended", "Passed", "Pending Refresher"
        elif drv_id == "DRV-1045":
            name     = "Khalid Al Remeithi"
            permit   = "Suspended"
            medical  = "Expired"
            training = "Pending Refresher"
            op_id    = "OP-004"
            operator = "Abu Dhabi Transport"
        else:
            permit   = "Suspended" if i % 10 == 3 else "Valid"
            medical  = "Expired"   if i % 12 == 5 else "Passed"
            training = "Pending Refresher" if i % 8 == 0 else "Complete"

        drivers_data.append((drv_id, name, permit, medical, training, operator, op_id))

    cursor.executemany("INSERT INTO drivers VALUES (?,?,?,?,?,?,?)", drivers_data)

    # ── VEHICLES (20) ─────────────────────────────────────────────────────
    # DRV-1001..DRV-1020 are the assigned bus drivers (one-to-one).
    # DRV-1021..DRV-1050 are unassigned (available for replacements).
    # AU-BUS-106 is the standby bus → no assigned driver.

    abu_dhabi_routes = [f"ADRoute-{n:02d}" for n in range(1, 19)]  # 18 routes

    vehicles_data = []
    for i in range(1, 21):
        veh_id = f"AU-BUS-{100 + i}"
        plate  = f"AD {20000 + i}"
        age    = random.randint(1, 8)
        gps    = "offline" if i == 7 else "online"
        insp   = "failed"  if i == 11 else "valid"
        cap    = random.choice([30, 40, 50])
        drv    = f"DRV-{1000 + i}"   # DRV-1001..DRV-1020

        if veh_id == "AU-BUS-104":
            occ, lat, lon = 12, 24.4490, 54.3600
            route = "ADRoute-04"
            insp  = "valid"
            gps   = "online"
        elif veh_id == "AU-BUS-106":
            occ, lat, lon = 0, 24.4539, 54.3773
            route = "Standby"
            insp  = "valid"
            gps   = "online"
            drv   = None   # standby has no assigned driver
        else:
            occ = random.randint(5, cap - 2)
            lat = 24.4539 + random.uniform(-0.05, 0.05)
            lon = 54.3773 + random.uniform(-0.05, 0.05)
            route = abu_dhabi_routes[(i - 1) % len(abu_dhabi_routes)]

        vehicles_data.append((veh_id, plate, age, gps, insp, cap, occ, lat, lon, route, drv))

    cursor.executemany("INSERT INTO vehicles VALUES (?,?,?,?,?,?,?,?,?,?,?)", vehicles_data)

    # ── ROADBLOCK (Khalidiyah area, Abu Dhabi, for route detour scenario) ───
    cursor.execute(
        "INSERT INTO roadblocks VALUES (?,?,?,?,?)",
        ("RB-ADEK-01", 24.4539, 54.3650, 100.0, "Khalidiyah Road Closure — Al Khaleej Al Arabi St")
    )

    # ── PARENTS (80) ──────────────────────────────────────────────────────
    par_first = ["Fatima", "Mariam", "Aisha", "Sara", "Noura", "Hind", "Layla", "Mona",
                 "Hassan", "Omar", "Saeed", "Rashid", "Hamdan", "Khalifa", "Ahmad", "Zayed"]
    par_last  = ["Al Mansoori", "Al Hashimi", "Al Remeithi", "Al Zaabi", "Al Hosani",
                 "Al Marzouqi", "Al Kaabi", "Al Suwaidi", "Al Dhaheri", "Al Mazrouei"]
    rels = ["Mother", "Father", "Mother", "Father", "Guardian"]

    parents_data = []
    for i in range(1, 81):
        par_id = f"PAR-{i:03d}"
        name   = f"{random.choice(par_first)} {random.choice(par_last)}"
        phone  = f"+971-5{random.randint(0,9)}-{random.randint(1000000, 9999999)}"
        email  = f"parent{i}@adek-families.ae"
        rel    = random.choice(rels)
        parents_data.append((par_id, name, phone, email, rel))

    cursor.executemany("INSERT INTO parents VALUES (?,?,?,?,?)", parents_data)

    # Build lookup: par_id → parent name (for guardian display field)
    par_name_map = {p[0]: p[1] for p in parents_data}

    # ── STUDENTS (200) — 10 per bus, each linked to a real bus and parent ─
    schools = [
        "Abu Dhabi International School",
        "GEMS World Academy Abu Dhabi",
        "The British School Al Khubairat",
        "ADEK Model School",
    ]
    stu_first = ["Ali", "Omar", "Fatima", "Sara", "Hamad", "Zayed", "Noura", "Hessa",
                 "Khalid", "Mariam", "Adam", "Layan", "Yousef", "Maryam", "Rashed", "Hind"]
    stu_last  = ["Al Mansoori", "Al Hashimi", "Al Remeithi", "Al Zaabi", "Al Hosani",
                 "Al Marzouqi", "Al Kaabi", "Al Suwaidi"]

    students_data = []
    stud_num = 1
    for bus_idx in range(1, 21):
        veh_id    = f"AU-BUS-{100 + bus_idx}"
        veh_route = vehicles_data[bus_idx - 1][9]       # assigned_route
        school    = schools[bus_idx % 4]

        for _ in range(10):
            stud_id  = f"STD-{10000 + stud_num}"
            name     = f"{random.choice(stu_first)} {random.choice(stu_last)}"
            par_id   = f"PAR-{random.randint(1, 80):03d}"
            guardian = par_name_map[par_id]             # parent's name for display
            behavior = f"Stage {random.randint(1, 3)}"
            students_data.append(
                (stud_id, name, school, veh_route, guardian, behavior, par_id, veh_id)
            )
            stud_num += 1

    cursor.executemany("INSERT INTO students VALUES (?,?,?,?,?,?,?,?)", students_data)

    # ── INCIDENTS (100) — only real driver-vehicle pairs ──────────────────
    incident_templates = [
        ("Driver Distraction",        "high", "Driver detected using mobile device at school zone."),
        ("Missing Guardian",          "med",  "Guardian not present at drop-off location."),
        ("Vehicle Inspection Failure","med",  "Pre-trip safety checklist failed."),
        ("Speed Violation",           "high", "Vehicle exceeded school zone speed limit."),
        ("Seatbelt Violation",        "med",  "Student detected without seatbelt in motion."),
        ("Minor Delay",               "low",  "Delay due to traffic congestion."),
        ("Route Deviation",           "med",  "Vehicle deviated from assigned route."),
    ]
    statuses = ["Resolved"]  # Historical incidents are always resolved; new ones come from live agent runs
    evidence_urls = [
        "https://storage.adek.gov.ae/evidence/collision_ch23.mp4",
        "https://storage.adek.gov.ae/evidence/distracted_drv_99.jpg",
        "https://storage.adek.gov.ae/evidence/telemetry_hb_02.csv",
        "https://storage.adek.gov.ae/evidence/handover_missing_std44.jpg",
        "None",
    ]

    # Real assigned pairs: DRV-100i drives AU-BUS-100i (i=1..20, skip bus 6 standby)
    real_pairs = [
        (f"DRV-{1000 + i}", f"AU-BUS-{100 + i}")
        for i in range(1, 21) if i != 6
    ]

    incidents_data = []
    for i in range(1, 101):
        inc_id = f"INC-2026-{i:04d}"
        inc_type, severity, desc = random.choice(incident_templates)
        drv_id, veh_id = random.choice(real_pairs)
        day = random.randint(1, 10)
        hr  = random.randint(7, 16)
        mn  = random.randint(0, 59)
        timestamp   = f"2026-06-{day:02d}T{hr:02d}:{mn:02d}:00"
        status      = random.choice(statuses)
        evidence    = random.choice(evidence_urls)
        incidents_data.append(
            (inc_id, severity, inc_type, drv_id, veh_id, timestamp, desc, status, evidence)
        )

    cursor.executemany("INSERT INTO incidents VALUES (?,?,?,?,?,?,?,?,?)", incidents_data)

    # ── STUDENT BOARDINGS (50) — students board their actual assigned bus ──
    boarding_sample = random.sample(students_data, 50)
    boardings_data  = []
    for i, stu in enumerate(boarding_sample):
        stud_id = stu[0]
        veh_id  = stu[7]            # assigned_vehicle_id
        bnd_id  = f"BND-{5001 + i}"
        etype   = random.choice(["boarding", "alighting"])
        day     = random.randint(1, 10)
        hr      = random.randint(7, 16)
        mn      = random.randint(0, 59)
        ts      = f"2026-06-{day:02d}T{hr:02d}:{mn:02d}:00"
        boardings_data.append((bnd_id, stud_id, veh_id, etype, ts))

    cursor.executemany("INSERT INTO student_boardings VALUES (?,?,?,?,?)", boardings_data)

    # ── FINES (30) — real driver-vehicle pairs ────────────────────────────
    fine_types = [
        ("Driver Distraction",        5000.0, "DMT"),
        ("Speed Violation",           3000.0, "DMT"),
        ("Seatbelt Violation",        1000.0, "ADEK"),
        ("Pre-trip Inspection Failure", 2000.0, "DMT"),
    ]
    fines_data = []
    for i in range(1, 31):
        drv_id, veh_id = random.choice(real_pairs)
        violation, amount, auth = random.choice(fine_types)
        day = random.randint(1, 10)
        hr  = random.randint(7, 16)
        mn  = random.randint(0, 59)
        ts  = f"2026-06-{day:02d}T{hr:02d}:{mn:02d}:00"
        fines_data.append((f"FINE-{2000 + i}", drv_id, veh_id, violation, amount, auth, ts))

    cursor.executemany("INSERT INTO fines VALUES (?,?,?,?,?,?,?)", fines_data)

    # ── COMPLIANCE SLAs (20) — linked to real incidents ───────────────────
    inc_ids   = [inc[0] for inc in incidents_data]
    slas_data = []
    for i in range(1, 21):
        drv_id, _ = random.choice(real_pairs)
        status    = "Completed" if i % 4 == 0 else "Pending"
        res_date  = "2026-06-09T14:30:00" if status == "Completed" else None
        slas_data.append((
            f"SLA-{3000 + i}", drv_id, random.choice(inc_ids),
            "2026-06-02T08:00:00", "2026-06-10T08:00:00", status, res_date
        ))

    cursor.executemany("INSERT INTO compliance_sla VALUES (?,?,?,?,?,?,?)", slas_data)

    # ── EDGE TELEMETRY (30) — real vehicles ───────────────────────────────
    tel_types = [
        ("Collision",        0.98, -1.2,  3.4, 0.5, "https://storage.adek.gov.ae/evidence/collision_ch23.mp4"),
        ("Phone_Usage",      0.95,  0.0,  0.0, 1.0, "https://storage.adek.gov.ae/evidence/distracted_drv_99.jpg"),
        ("Harsh_Brake",      0.88, -0.9, -2.1, 0.1, "https://storage.adek.gov.ae/evidence/telemetry_hb_02.csv"),
        ("Missing_Guardian", 0.99,  0.0,  0.0, 0.0, "https://storage.adek.gov.ae/evidence/handover_missing_std44.jpg"),
    ]
    real_veh_ids  = [f"AU-BUS-{100 + i}" for i in range(1, 21)]
    telemetry_data = []
    for i in range(1, 31):
        veh_id                       = random.choice(real_veh_ids)
        etype, conf, gx, gy, gz, url = random.choice(tel_types)
        day = random.randint(1, 10)
        hr  = random.randint(7, 16)
        mn  = random.randint(0, 59)
        ts  = f"2026-06-{day:02d}T{hr:02d}:{mn:02d}:00"
        telemetry_data.append((f"EVT-{4000 + i}", veh_id, etype, conf, gx, gy, gz, url, ts))

    cursor.executemany("INSERT INTO edge_telemetry VALUES (?,?,?,?,?,?,?,?,?)", telemetry_data)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    seed_database()
    print("Database seeded successfully!")
