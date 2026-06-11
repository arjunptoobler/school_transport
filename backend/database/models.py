from pydantic import BaseModel
from typing import Optional


class OperatorModel(BaseModel):
    operator_id: str
    name: str
    license_no: str
    contact_email: str
    contact_phone: str
    hq_location: str


class DriverModel(BaseModel):
    driver_id: str
    name: str
    permit_status: str
    medical_status: str
    training_status: str
    operator: str
    operator_id: Optional[str] = None


class VehicleModel(BaseModel):
    vehicle_id: str
    license_plate: str
    age: int
    gps_status: str
    inspection_status: str
    capacity: int
    current_occupancy: int
    current_lat: float
    current_lon: float
    assigned_route: str
    assigned_driver_id: Optional[str] = None


class ParentModel(BaseModel):
    parent_id: str
    name: str
    phone: str
    email: str
    relationship: str


class StudentModel(BaseModel):
    student_id: str
    name: str
    school: str
    route: str
    guardian: str
    behavior_stage: str
    parent_id: Optional[str] = None
    assigned_vehicle_id: Optional[str] = None


class IncidentModel(BaseModel):
    incident_id: str
    severity: str
    type: str
    driver_id: str
    vehicle_id: str
    timestamp: str
    description: str
    status: Optional[str] = None
    evidence_url: Optional[str] = None
