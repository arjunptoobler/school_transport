from pydantic import BaseModel

class DriverModel(BaseModel):
    driver_id: str
    name: str
    permit_status: str
    medical_status: str
    training_status: str
    operator: str

class VehicleModel(BaseModel):
    vehicle_id: str
    license_plate: str
    age: int
    gps_status: str
    inspection_status: str

class StudentModel(BaseModel):
    student_id: str
    name: str
    school: str
    route: str
    guardian: str
    behavior_stage: str

class IncidentModel(BaseModel):
    incident_id: str
    severity: str
    type: str
    driver_id: str
    vehicle_id: str
    timestamp: str
    description: str
