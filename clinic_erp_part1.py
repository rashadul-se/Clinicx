"""
Clinic Management System ERP - Database Models and Core Classes
Production-ready implementation with OOP, security, and optimization
"""

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, EmailStr, Field, validator
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    ForeignKey, Text, Date, Time, Index, CheckConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import hashlib
import secrets
import re

Base = declarative_base()

# ==================== ENUMS ====================

class UserRole(str, Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    NURSE = "nurse"
    PHARMACIST = "pharmacist"
    RECEPTIONIST = "receptionist"
    PATIENT = "patient"
    MANAGER = "manager"
    VENDOR = "vendor"

class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

class PrescriptionStatus(str, Enum):
    PENDING = "pending"
    DISPENSED = "dispensed"
    PARTIALLY_DISPENSED = "partially_dispensed"
    CANCELLED = "cancelled"

class ConsultationType(str, Enum):
    IN_PERSON = "in_person"
    TELECONSULTATION = "teleconsultation"
    EMERGENCY = "emergency"

# ==================== DATABASE MODELS ====================

class User(Base):
    """Base user model with RBAC and security features"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    salt = Column(String(64), nullable=False)
    role = Column(String(50), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(32), nullable=True)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    audit_logs = relationship("AuditLog", back_populates="user")
    
    __table_args__ = (
        Index('idx_user_role_active', 'role', 'is_active'),
    )

class Patient(Base):
    """Patient model with EHR integration"""
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    pid = Column(String(50), unique=True, nullable=False, index=True)  # Unique Patient ID
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(20))
    phone = Column(String(20), index=True)
    email = Column(String(255))
    postal_code = Column(String(20), nullable=False, index=True)
    address = Column(Text)
    emergency_contact = Column(String(100))
    emergency_phone = Column(String(20))
    blood_group = Column(String(10))
    allergies = Column(Text)  # JSON stored as text
    chronic_conditions = Column(Text)  # JSON stored as text
    insurance_provider = Column(String(200))
    insurance_number = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    appointments = relationship("Appointment", back_populates="patient")
    prescriptions = relationship("Prescription", back_populates="patient")
    medical_records = relationship("MedicalRecord", back_populates="patient")
    
    __table_args__ = (
        Index('idx_patient_name', 'last_name', 'first_name'),
        Index('idx_patient_postal', 'postal_code'),
    )

class Doctor(Base):
    """Doctor model with credentials and scheduling"""
    __tablename__ = "doctors"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    specialty = Column(String(200), index=True)
    license_number = Column(String(100), unique=True)
    license_expiry = Column(Date)
    qualification = Column(Text)
    consultation_fee = Column(Float, default=0.0)
    teleconsultation_fee = Column(Float, default=0.0)
    available_for_teleconsult = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    appointments = relationship("Appointment", back_populates="doctor")
    prescriptions = relationship("Prescription", back_populates="doctor")
    schedules = relationship("DoctorSchedule", back_populates="doctor")
    
    __table_args__ = (
        Index('idx_doctor_specialty', 'specialty'),
    )

class DoctorSchedule(Base):
    """Doctor availability schedule"""
    __tablename__ = "doctor_schedules"
    
    id = Column(Integer, primary_key=True, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False)
    day_of_week = Column(Integer, nullable=False)  # 0=Monday, 6=Sunday
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    consultation_type = Column(String(50), default="in_person")
    is_active = Column(Boolean, default=True)
    
    doctor = relationship("Doctor", back_populates="schedules")
    
    __table_args__ = (
        Index('idx_schedule_doctor_day', 'doctor_id', 'day_of_week'),
    )

class Appointment(Base):
    """Appointment booking with teleconsultation support"""
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    appointment_date = Column(Date, nullable=False, index=True)
    appointment_time = Column(Time, nullable=False)
    consultation_type = Column(String(50), default="in_person")
    status = Column(String(50), default="scheduled", index=True)
    chief_complaint = Column(Text)
    notes = Column(Text)
    video_room_id = Column(String(100), nullable=True)  # For teleconsultation
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    patient = relationship("Patient", back_populates="appointments")
    doctor = relationship("Doctor", back_populates="appointments")
    medical_record = relationship("MedicalRecord", back_populates="appointment", uselist=False)
    
    __table_args__ = (
        Index('idx_appointment_date_doctor', 'appointment_date', 'doctor_id'),
        Index('idx_appointment_status', 'status', 'appointment_date'),
    )

class MedicalRecord(Base):
    """SOAP notes and clinical documentation"""
    __tablename__ = "medical_records"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True, unique=True)
    subjective = Column(Text)  # Patient's complaint
    objective = Column(Text)  # Physical exam findings
    assessment = Column(Text)  # Diagnosis
    plan = Column(Text)  # Treatment plan
    vitals = Column(Text)  # JSON: BP, pulse, temp, etc.
    lab_results = Column(Text)  # JSON
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    patient = relationship("Patient", back_populates="medical_records")
    appointment = relationship("Appointment", back_populates="medical_record")
    
    __table_args__ = (
        Index('idx_medical_record_patient', 'patient_id', 'created_at'),
    )

class Medicine(Base):
    """Medicine inventory master data"""
    __tablename__ = "medicines"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    generic_name = Column(String(200), index=True)
    manufacturer = Column(String(200))
    category = Column(String(100), index=True)
    dosage_form = Column(String(50))  # tablet, syrup, injection
    strength = Column(String(50))
    unit_price = Column(Float, nullable=False)
    reorder_level = Column(Integer, default=50)
    is_controlled_substance = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    stock_items = relationship("MedicineStock", back_populates="medicine")
    prescription_items = relationship("PrescriptionItem", back_populates="medicine")
    
    __table_args__ = (
        Index('idx_medicine_name', 'name'),
        CheckConstraint('unit_price >= 0', name='check_medicine_price'),
    )

class MedicineStock(Base):
    """Inventory tracking with FIFO and expiry management"""
    __tablename__ = "medicine_stocks"
    
    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)
    batch_number = Column(String(100), nullable=False)
    expiry_date = Column(Date, nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    location = Column(String(100))  # warehouse, pharmacy, ward
    cost_price = Column(Float)
    supplier = Column(String(200))
    received_date = Column(Date, default=date.today)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    medicine = relationship("Medicine", back_populates="stock_items")
    
    __table_args__ = (
        Index('idx_stock_medicine_expiry', 'medicine_id', 'expiry_date'),
        Index('idx_stock_location', 'location', 'medicine_id'),
        CheckConstraint('quantity >= 0', name='check_stock_quantity'),
    )

class Prescription(Base):
    """E-prescription with drug interaction checking"""
    __tablename__ = "prescriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    prescription_date = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(String(50), default="pending")
    diagnosis = Column(Text)
    notes = Column(Text)
    valid_until = Column(Date)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    patient = relationship("Patient", back_populates="prescriptions")
    doctor = relationship("Doctor", back_populates="prescriptions")
    items = relationship("PrescriptionItem", back_populates="prescription")
    
    __table_args__ = (
        Index('idx_prescription_patient_date', 'patient_id', 'prescription_date'),
    )

class PrescriptionItem(Base):
    """Individual medicine items in prescription"""
    __tablename__ = "prescription_items"
    
    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False)
    dosage = Column(String(100), nullable=False)
    frequency = Column(String(100), nullable=False)
    duration = Column(String(100), nullable=False)
    quantity = Column(Integer, nullable=False)
    instructions = Column(Text)
    dispensed_quantity = Column(Integer, default=0)
    
    prescription = relationship("Prescription", back_populates="items")
    medicine = relationship("Medicine", back_populates="prescription_items")
    
    __table_args__ = (
        CheckConstraint('quantity > 0', name='check_prescription_quantity'),
    )

class AuditLog(Base):
    """Comprehensive audit trail for compliance"""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(Integer)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    details = Column(Text)  # JSON
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    user = relationship("User", back_populates="audit_logs")
    
    __table_args__ = (
        Index('idx_audit_user_time', 'user_id', 'timestamp'),
        Index('idx_audit_action_time', 'action', 'timestamp'),
    )

class PostalCodeCluster(Base):
    """Location intelligence for patient clustering"""
    __tablename__ = "postal_code_clusters"
    
    id = Column(Integer, primary_key=True, index=True)
    postal_code = Column(String(20), unique=True, nullable=False, index=True)
    cluster_name = Column(String(100))
    region = Column(String(100), index=True)
    patient_count = Column(Integer, default=0)
    avg_consultation_fee = Column(Float)
    specialty_demand = Column(Text)  # JSON
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_postal_cluster', 'cluster_name', 'region'),
    )

# ==================== PYDANTIC MODELS FOR API ====================

class UserLogin(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    mfa_code: Optional[str] = None

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain lowercase letter')
        if not re.search(r'\d', v):
            raise ValueError('Password must contain digit')
        return v

class PatientCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    date_of_birth: date
    gender: str
    phone: str = Field(..., regex=r'^\+?[\d\s\-\(\)]+$')
    email: Optional[EmailStr] = None
    postal_code: str = Field(..., min_length=3, max_length=20)
    address: str
    blood_group: Optional[str] = None
    allergies: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_number: Optional[str] = None

class AppointmentCreate(BaseModel):
    patient_id: int = Field(..., gt=0)
    doctor_id: int = Field(..., gt=0)
    appointment_date: date
    appointment_time: str
    consultation_type: ConsultationType = ConsultationType.IN_PERSON
    chief_complaint: Optional[str] = None

class PrescriptionCreate(BaseModel):
    patient_id: int = Field(..., gt=0)
    doctor_id: int = Field(..., gt=0)
    diagnosis: str
    items: List[Dict[str, Any]]
    notes: Optional[str] = None

# ==================== SECURITY UTILITIES ====================

class SecurityManager:
    """Handles password hashing and security operations"""
    
    @staticmethod
    def generate_salt() -> str:
        return secrets.token_hex(32)
    
    @staticmethod
    def hash_password(password: str, salt: str) -> str:
        pwd_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        return hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt_bytes, 100000).hex()
    
    @staticmethod
    def verify_password(password: str, salt: str, password_hash: str) -> bool:
        return SecurityManager.hash_password(password, salt) == password_hash
    
    @staticmethod
    def generate_mfa_secret() -> str:
        return secrets.token_urlsafe(16)

print("✅ Core database models and security utilities loaded successfully!")
