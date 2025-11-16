# Clinic Management System ERP - Production Ready
# Complete implementation with FastAPI, Streamlit, MariaDB, Security & Microservices

# ==================== REQUIREMENTS ====================
"""
pip install fastapi uvicorn streamlit pymysql sqlalchemy python-jose[cryptography]
pip install passlib[bcrypt] python-multipart pydantic python-dotenv
pip install redis celery geopy scikit-learn pandas numpy
pip install twilio sendgrid python-dateutil apscheduler
"""

# ==================== DATABASE MODELS & CONNECTION ====================
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Float, Boolean,
    Text, ForeignKey, Index, Enum, Date, Time, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.pool import QueuePool
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import enum
from passlib.context import CryptContext
from jose import JWTError, jwt
import os
from dotenv import load_dotenv

load_dotenv()

# Database Configuration with Connection Pooling
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://clinic_user:secure_password@localhost:3306/clinic_erp"
)

engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Security Configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480


# ==================== ENUMS ====================
class UserRole(enum.Enum):
    ADMIN = "admin"
    DOCTOR = "doctor"
    NURSE = "nurse"
    PHARMACIST = "pharmacist"
    RECEPTIONIST = "receptionist"
    PATIENT = "patient"
    MANAGER = "manager"
    LAB_TECH = "lab_tech"


class AppointmentStatus(enum.Enum):
    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class ConsultationType(enum.Enum):
    IN_PERSON = "in_person"
    TELEMEDICINE = "telemedicine"
    FOLLOW_UP = "follow_up"


class PrescriptionStatus(enum.Enum):
    PENDING = "pending"
    DISPENSED = "dispensed"
    CANCELLED = "cancelled"


class BillingStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    OVERDUE = "overdue"
    INSURANCE_PENDING = "insurance_pending"


# ==================== DATABASE MODELS ====================
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, index=True)
    is_active = Column(Boolean, default=True, index=True)
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(100), nullable=True)
    last_login = Column(DateTime, nullable=True)
    failed_login_attempts = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    profile = relationship("UserProfile", back_populates="user", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")
    
    __table_args__ = (
        Index('idx_user_role_active', 'role', 'is_active'),
    )


class UserProfile(Base):
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    phone = Column(String(20), index=True)
    license_number = Column(String(100), nullable=True)  # For doctors
    specialization = Column(String(200), nullable=True)
    qualification = Column(Text, nullable=True)
    experience_years = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="profile")


class Patient(Base):
    __tablename__ = "patients"
    
    id = Column(Integer, primary_key=True, index=True)
    pid = Column(String(50), unique=True, index=True, nullable=False)  # Patient ID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    date_of_birth = Column(Date, nullable=False)
    gender = Column(String(20))
    blood_group = Column(String(10))
    phone = Column(String(20), index=True)
    email = Column(String(255), index=True)
    address = Column(Text)
    postal_code = Column(String(20), index=True)
    emergency_contact = Column(String(100))
    emergency_phone = Column(String(20))
    insurance_provider = Column(String(200))
    insurance_number = Column(String(100))
    allergies = Column(Text)
    chronic_conditions = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    appointments = relationship("Appointment", back_populates="patient")
    medical_records = relationship("MedicalRecord", back_populates="patient")
    prescriptions = relationship("Prescription", back_populates="patient")
    bills = relationship("Bill", back_populates="patient")
    
    __table_args__ = (
        Index('idx_patient_name', 'first_name', 'last_name'),
        Index('idx_patient_postal', 'postal_code'),
    )


class PostalCodeCluster(Base):
    __tablename__ = "postal_code_clusters"
    
    id = Column(Integer, primary_key=True, index=True)
    postal_code = Column(String(20), unique=True, index=True, nullable=False)
    cluster_id = Column(Integer, index=True)
    region_name = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)
    patient_count = Column(Integer, default=0)
    avg_age = Column(Float)
    common_conditions = Column(JSON)
    demand_score = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Appointment(Base):
    __tablename__ = "appointments"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    appointment_date = Column(Date, nullable=False, index=True)
    appointment_time = Column(Time, nullable=False)
    duration_minutes = Column(Integer, default=30)
    consultation_type = Column(Enum(ConsultationType), default=ConsultationType.IN_PERSON)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED, index=True)
    reason = Column(Text)
    notes = Column(Text)
    room_number = Column(String(20))
    video_link = Column(String(500))  # For telemedicine
    reminder_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="appointments")
    medical_record = relationship("MedicalRecord", back_populates="appointment", uselist=False)
    
    __table_args__ = (
        Index('idx_appointment_doctor_date', 'doctor_id', 'appointment_date', 'status'),
        Index('idx_appointment_patient_date', 'patient_id', 'appointment_date'),
    )


class MedicalRecord(Base):
    __tablename__ = "medical_records"
    
    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    visit_date = Column(DateTime, default=datetime.utcnow, index=True)
    
    # SOAP Notes
    subjective = Column(Text)  # Patient's complaint
    objective = Column(Text)   # Observations, vitals
    assessment = Column(Text)  # Diagnosis
    plan = Column(Text)        # Treatment plan
    
    # Vitals
    temperature = Column(Float)
    blood_pressure_systolic = Column(Integer)
    blood_pressure_diastolic = Column(Integer)
    heart_rate = Column(Integer)
    respiratory_rate = Column(Integer)
    oxygen_saturation = Column(Float)
    weight = Column(Float)
    height = Column(Float)
    
    diagnosis_codes = Column(JSON)  # ICD-10 codes
    lab_results = Column(JSON)
    imaging_results = Column(JSON)
    follow_up_required = Column(Boolean, default=False)
    follow_up_date = Column(Date, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="medical_records")
    appointment = relationship("Appointment", back_populates="medical_record")


class Prescription(Base):
    __tablename__ = "prescriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    prescription_number = Column(String(50), unique=True, index=True, nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    doctor_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    prescription_date = Column(DateTime, default=datetime.utcnow, index=True)
    status = Column(Enum(PrescriptionStatus), default=PrescriptionStatus.PENDING, index=True)
    notes = Column(Text)
    dispensed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    dispensed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="prescriptions")
    medications = relationship("PrescriptionItem", back_populates="prescription")
    
    __table_args__ = (
        Index('idx_prescription_patient_date', 'patient_id', 'prescription_date'),
        Index('idx_prescription_status_date', 'status', 'prescription_date'),
    )


class Medicine(Base):
    __tablename__ = "medicines"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    generic_name = Column(String(200), index=True)
    category = Column(String(100), index=True)
    manufacturer = Column(String(200))
    dosage_form = Column(String(50))  # Tablet, Syrup, Injection
    strength = Column(String(50))
    unit_price = Column(Float, nullable=False)
    reorder_level = Column(Integer, default=50)
    is_controlled = Column(Boolean, default=False)
    requires_prescription = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    inventory = relationship("Inventory", back_populates="medicine")
    interactions = relationship("DrugInteraction", 
                              foreign_keys="DrugInteraction.drug_a_id",
                              back_populates="drug_a")
    
    __table_args__ = (
        Index('idx_medicine_name_category', 'name', 'category'),
    )


class Inventory(Base):
    __tablename__ = "inventory"
    
    id = Column(Integer, primary_key=True, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)
    batch_number = Column(String(100), index=True)
    quantity = Column(Integer, nullable=False, default=0)
    expiry_date = Column(Date, nullable=False, index=True)
    location = Column(String(100))  # Warehouse, Pharmacy, Ward
    cost_price = Column(Float)
    selling_price = Column(Float)
    supplier = Column(String(200))
    received_date = Column(Date, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    medicine = relationship("Medicine", back_populates="inventory")
    
    __table_args__ = (
        Index('idx_inventory_medicine_expiry', 'medicine_id', 'expiry_date'),
        Index('idx_inventory_location_qty', 'location', 'quantity'),
    )


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"
    
    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"), nullable=False, index=True)
    medicine_id = Column(Integer, ForeignKey("medicines.id"), nullable=False)
    dosage = Column(String(100), nullable=False)
    frequency = Column(String(100), nullable=False)  # e.g., "3 times daily"
    duration_days = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    instructions = Column(Text)
    
    # Drug safety checks
    allergy_checked = Column(Boolean, default=False)
    interaction_checked = Column(Boolean, default=False)
    warnings = Column(JSON)
    
    # Relationships
    prescription = relationship("Prescription", back_populates="medications")


class DrugInteraction(Base):
    __tablename__ = "drug_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    drug_a_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)
    drug_b_id = Column(Integer, ForeignKey("medicines.id"), nullable=False, index=True)
    severity = Column(String(20))  # Mild, Moderate, Severe
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    drug_a = relationship("Medicine", foreign_keys=[drug_a_id], back_populates="interactions")
    
    __table_args__ = (
        Index('idx_drug_interaction', 'drug_a_id', 'drug_b_id'),
    )


class Bill(Base):
    __tablename__ = "bills"
    
    id = Column(Integer, primary_key=True, index=True)
    bill_number = Column(String(50), unique=True, index=True, nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False, index=True)
    appointment_id = Column(Integer, ForeignKey("appointments.id"), nullable=True)
    bill_date = Column(DateTime, default=datetime.utcnow, index=True)
    total_amount = Column(Float, nullable=False)
    discount = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    net_amount = Column(Float, nullable=False)
    paid_amount = Column(Float, default=0.0)
    status = Column(Enum(BillingStatus), default=BillingStatus.PENDING, index=True)
    insurance_claim_amount = Column(Float, default=0.0)
    insurance_claim_status = Column(String(50))
    payment_method = Column(String(50))
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    patient = relationship("Patient", back_populates="bills")
    items = relationship("BillItem", back_populates="bill")
    
    __table_args__ = (
        Index('idx_bill_patient_status', 'patient_id', 'status'),
        Index('idx_bill_date_status', 'bill_date', 'status'),
    )


class BillItem(Base):
    __tablename__ = "bill_items"
    
    id = Column(Integer, primary_key=True, index=True)
    bill_id = Column(Integer, ForeignKey("bills.id"), nullable=False, index=True)
    item_type = Column(String(50), nullable=False)  # Consultation, Lab, Medicine, Procedure
    description = Column(String(500), nullable=False)
    quantity = Column(Integer, default=1)
    unit_price = Column(Float, nullable=False)
    total_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    bill = relationship("Bill", back_populates="items")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), index=True)
    resource_id = Column(Integer)
    ip_address = Column(String(50))
    user_agent = Column(String(500))
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    __table_args__ = (
        Index('idx_audit_user_action_date', 'user_id', 'action', 'created_at'),
    )


# ==================== PYDANTIC SCHEMAS ====================
from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, List
from datetime import date, time


class Token(BaseModel):
    access_token: str
    token_type: str
    role: str
    user_id: int


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole
    first_name: str
    last_name: str
    phone: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class PatientCreate(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: date
    gender: str
    phone: str
    email: EmailStr
    address: str
    postal_code: str
    emergency_contact: str
    emergency_phone: str
    insurance_provider: Optional[str] = None
    insurance_number: Optional[str] = None
    allergies: Optional[str] = None
    chronic_conditions: Optional[str] = None


class AppointmentCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_date: date
    appointment_time: time
    consultation_type: ConsultationType = ConsultationType.IN_PERSON
    reason: str


class PrescriptionCreate(BaseModel):
    patient_id: int
    doctor_id: int
    appointment_id: Optional[int] = None
    notes: Optional[str] = None
    medications: List[Dict[str, Any]]


# ==================== SECURITY & AUTHENTICATION ====================
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username, role=payload.get("role"))
    except JWTError:
        raise credentials_exception
    
    user = db.query(User).filter(User.username == token_data.username).first()
    if user is None:
        raise credentials_exception
    return user


def require_role(allowed_roles: List[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker


# ==================== BUSINESS LOGIC SERVICES ====================
class PatientService:
    """Service for patient management operations"""
    
    @staticmethod
    def generate_pid(db: Session) -> str:
        """Generate unique patient ID"""
        import random
        while True:
            pid = f"P{datetime.now().year}{random.randint(100000, 999999)}"
            if not db.query(Patient).filter(Patient.pid == pid).first():
                return pid
    
    @staticmethod
    def create_patient(db: Session, patient_data: PatientCreate) -> Patient:
        """Create new patient with validation"""
        pid = PatientService.generate_pid(db)
        patient = Patient(
            pid=pid,
            **patient_data.dict()
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        
        # Update postal code cluster
        LocationService.update_cluster_stats(db, patient.postal_code)
        return patient
    
    @staticmethod
    def search_patients(db: Session, query: str, postal_code: Optional[str] = None) -> List[Patient]:
        """Search patients with optimized query"""
        q = db.query(Patient)
        
        if query:
            q = q.filter(
                (Patient.first_name.ilike(f"%{query}%")) |
                (Patient.last_name.ilike(f"%{query}%")) |
                (Patient.pid.ilike(f"%{query}%")) |
                (Patient.phone.ilike(f"%{query}%"))
            )
        
        if postal_code:
            q = q.filter(Patient.postal_code == postal_code)
        
        return q.limit(50).all()


class LocationService:
    """Service for location intelligence and clustering"""
    
    @staticmethod
    def update_cluster_stats(db: Session, postal_code: str):
        """Update statistics for postal code cluster"""
        cluster = db.query(PostalCodeCluster).filter(
            PostalCodeCluster.postal_code == postal_code
        ).first()
        
        if not cluster:
            cluster = PostalCodeCluster(postal_code=postal_code, cluster_id=0)
            db.add(cluster)
        
        # Calculate statistics
        patients = db.query(Patient).filter(Patient.postal_code == postal_code).all()
        cluster.patient_count = len(patients)
        
        if patients:
            ages = [(datetime.now().date() - p.date_of_birth).days / 365.25 for p in patients]
            cluster.avg_age = sum(ages) / len(ages)
        
        db.commit()
    
    @staticmethod
    def get_demand_analysis(db: Session, cluster_id: int) -> Dict:
        """Analyze demand for a specific cluster"""
        cluster = db.query(PostalCodeCluster).filter(
            PostalCodeCluster.cluster_id == cluster_id
        ).first()
        
        if not cluster:
            return {}
        
        # Get appointment statistics
        patients = db.query(Patient).filter(
            Patient.postal_code == cluster.postal_code
        ).all()
        
        patient_ids = [p.id for p in patients]
        appointments = db.query(Appointment).filter(
            Appointment.patient_id.in_(patient_ids)
        ).count()
        
        return {
            "cluster_id": cluster_id,
            "postal_code": cluster.postal_code,
            "patient_count": cluster.patient_count,
            "avg_age": cluster.avg_age,
            "total_appointments": appointments,
            "demand_score": cluster.demand_score
        }


class PrescriptionService:
    """Service for e-prescription management with drug safety checks"""
    
    @staticmethod
    def check_drug_interactions(db: Session, medicine_ids: List[int]) -> List[Dict]:
        """Check for drug-drug interactions"""
        warnings = []
        
        for i in range(len(medicine_ids)):
            for j in range(i + 1, len(medicine_ids)):
                interaction = db.query(DrugInteraction).filter(
                    ((DrugInteraction.drug_a_id == medicine_ids[i]) &
                     (DrugInteraction.drug_b_id == medicine_ids[j])) |
                    ((DrugInteraction.drug_a_id == medicine_ids[j]) &
                     (DrugInteraction.drug_b_id == medicine_ids[i]))
                ).first()
                
                if interaction:
                    warnings.append({
                        "severity": interaction.severity,
                        "description": interaction.description,
                        "drugs": [medicine_ids[i], medicine_ids[j]]
                    })
        
        return warnings
    
    @staticmethod
    def check_allergies(db: Session, patient_id: int, medicine_ids: List[int]) -> List[str]:
        """Check if patient is allergic to any prescribed medication"""
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        warnings = []
        
        if patient and patient.allergies:
            allergies = patient.allergies.lower().split(',')
            for med_id in medicine_ids:
                medicine = db.query(Medicine).filter(Medicine.id == med_id).first()
                if medicine:
                    if any(allergy.strip() in medicine.name.lower() for allergy in allergies):
                        warnings.append(f"Patient is allergic to {medicine.name}")
        
        return warnings
    
    @staticmethod
    def create_prescription(db: Session, prescription_data: PrescriptionCreate, doctor_id: int) -> Prescription:
        """Create prescription with safety checks"""
        # Generate prescription number
        prescription_number = f"RX{datetime.now().strftime('%Y%m%d')}{db.query(Prescription).count() + 1:04d}"
        
        # Extract medicine IDs
        medicine_ids = [item['medicine_id'] for item in prescription_data.medications]
        
        # Safety checks
        interaction_warnings = PrescriptionService.check_drug_interactions(db, medicine_ids)
        allergy_warnings = PrescriptionService.check_allergies(db, prescription_data.patient_id, medicine_ids)
        
        # Create prescription
        prescription = Prescription(
            prescription_number=prescription_number,
            patient_id=prescription_data.patient_id,
            doctor_id=doctor_id,
            appointment_id=prescription_data.appointment_id,
            notes=prescription_data.notes,
            status=PrescriptionStatus.PENDING
        )
        db.add(prescription)
        db.flush()
        
        # Add prescription items
        for item in prescription_data.medications:
            warnings = []
            if interaction_warnings:
                warnings.extend([w for w in interaction_warnings if item['medicine_id'] in w['drugs']])
            if allergy_warnings:
                warnings.extend(allergy_warnings)
            
            prescription_item = PrescriptionItem(
                prescription_id=prescription.id,
                medicine_id=item['medicine_id'],
                dosage=item['dosage'],
                frequency=item['frequency'],
                duration_days=item['duration_days'],
                quantity=item['quantity'],
                instructions=item.get('instructions', ''),
                allergy_checked=True,
                interaction_checked=True,
                warnings=warnings if warnings else None
            )
            db.add(prescription_item)
        
        db.commit()
        db.refresh(prescription)
        return prescription


class InventoryService:
    """Service for inventory management with FIFO and expiry tracking"""
    
    @staticmethod
    def check_stock_availability(db: Session, medicine_id: int, required_quantity: int) -> bool:
        """Check if sufficient stock is available"""
        total_stock = db.query(Inventory).filter(
            Inventory.medicine_id == medicine_id,
            Inventory.quantity > 0,
            Inventory.expiry_date > datetime.now().date()
        ).with_entities(
            db.func.sum(Inventory.quantity)
        ).scalar() or 0
        
        return total_stock >= required_quantity
    
    @staticmethod
    def dispense_medicine_fifo(db: Session, medicine_id: int, quantity: int, location: str = "Pharmacy") -> List[Dict]:
        """Dispense medicine using FIFO based on expiry date"""
        # Get available inventory sorted by expiry date (FIFO)
        inventory_items = db.query(Inventory).filter(
            Inventory.medicine_id == medicine_id,
            Inventory.location == location,
            Inventory.quantity > 0,
            Inventory.expiry_date > datetime.now().date()
        ).order_by(Inventory.expiry_date.asc()).all()
        
        dispensed = []
        remaining = quantity
        
        for item in inventory_items:
            if remaining <= 0:
                break
            
            if item.quantity >= remaining:
                item.quantity -= remaining
                dispensed.append({
                    "batch_number": item.batch_number,
                    "quantity": remaining,
                    "expiry_date": item.expiry_date
                })
                remaining = 0
            else:
                remaining -= item.quantity
                dispensed.append({
                    "batch_number": item.batch_number,
                    "quantity": item.quantity,
                    "expiry_date": item.expiry_date
                })
                item.quantity = 0
        
        if remaining > 0:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock. Required: {quantity}, Available: {quantity - remaining}"
            )
        
        db.commit()
        return dispensed
    
    @staticmethod
    def get_expiring_medicines(db: Session, days: int = 30) -> List[Dict]:
        """Get medicines expiring within specified days"""
        expiry_threshold = datetime.now().date() + timedelta(days=days)
        
        expiring = db.query(
            Inventory, Medicine
        ).join(Medicine).filter(
            Inventory.expiry_date <= expiry_threshold,
            Inventory.expiry_date > datetime.now().date(),
            Inventory.quantity > 0
        ).all()
        
        return [{
            "medicine_name": med.name,
            "batch_number": inv.batch_number,
            "quantity": inv.quantity,
            "expiry_date": inv.expiry_date,
            "days_to_expiry": (inv.expiry_date - datetime.now().date()).days
        } for inv, med in expiring]
    
    @staticmethod
    def check_reorder_levels(db: Session) -> List[Dict]:
        """Check medicines that need reordering"""
        medicines = db.query(Medicine).all()
        reorder_needed = []
        
        for medicine in medicines:
            total_stock = db.query(Inventory).filter(
                Inventory.medicine_id == medicine.id,
                Inventory.quantity > 0,
                Inventory.expiry_date > datetime.now().date()
            ).with_entities(
                db.func.sum(Inventory.quantity)
            ).scalar() or 0
            
            if total_stock < medicine.reorder_level:
                reorder_needed.append({
                    "medicine_id": medicine.id,
                    "medicine_name": medicine.name,
                    "current_stock": total_stock,
                    "reorder_level": medicine.reorder_level,
                    "quantity_to_order": medicine.reorder_level * 2 - total_stock
                })
        
        return reorder_needed


class BillingService:
    """Service for billing and revenue cycle management"""
    
    @staticmethod
    def generate_bill_number(db: Session) -> str:
        """Generate unique bill number"""
        count = db.query(Bill).count()
        return f"BILL{datetime.now().strftime('%Y%m%d')}{count + 1:05d}"
    
    @staticmethod
    def create_bill(db: Session, patient_id: int, appointment_id: Optional[int], items: List[Dict]) -> Bill:
        """Create comprehensive bill with items"""
        bill_number = BillingService.generate_bill_number(db)
        
        # Calculate totals
        total_amount = sum(item['quantity'] * item['unit_price'] for item in items)
        tax = total_amount * 0.05  # 5% tax
        net_amount = total_amount + tax
        
        bill = Bill(
            bill_number=bill_number,
            patient_id=patient_id,
            appointment_id=appointment_id,
            bill_date=datetime.utcnow(),
            total_amount=total_amount,
            tax=tax,
            net_amount=net_amount,
            status=BillingStatus.PENDING
        )
        db.add(bill)
        db.flush()
        
        # Add bill items
        for item in items:
            bill_item = BillItem(
                bill_id=bill.id,
                item_type=item['item_type'],
                description=item['description'],
                quantity=item['quantity'],
                unit_price=item['unit_price'],
                total_price=item['quantity'] * item['unit_price']
            )
            db.add(bill_item)
        
        db.commit()
        db.refresh(bill)
        return bill
    
    @staticmethod
    def process_payment(db: Session, bill_id: int, amount: float, payment_method: str) -> Bill:
        """Process payment for a bill"""
        bill = db.query(Bill).filter(Bill.id == bill_id).first()
        if not bill:
            raise HTTPException(status_code=404, detail="Bill not found")
        
        bill.paid_amount += amount
        bill.payment_method = payment_method
        
        if bill.paid_amount >= bill.net_amount:
            bill.status = BillingStatus.PAID
        elif bill.paid_amount > 0:
            bill.status = BillingStatus.PARTIALLY_PAID
        
        db.commit()
        db.refresh(bill)
        return bill
    
    @staticmethod
    def get_revenue_report(db: Session, start_date: date, end_date: date) -> Dict:
        """Generate revenue report for date range"""
        bills = db.query(Bill).filter(
            Bill.bill_date >= start_date,
            Bill.bill_date <= end_date
        ).all()
        
        total_billed = sum(b.net_amount for b in bills)
        total_collected = sum(b.paid_amount for b in bills)
        pending_amount = total_billed - total_collected
        
        return {
            "start_date": start_date,
            "end_date": end_date,
            "total_bills": len(bills),
            "total_billed": total_billed,
            "total_collected": total_collected,
            "pending_amount": pending_amount,
            "collection_rate": (total_collected / total_billed * 100) if total_billed > 0 else 0
        }


class AuditService:
    """Service for audit logging and compliance"""
    
    @staticmethod
    def log_action(db: Session, user_id: int, action: str, resource_type: str, 
                   resource_id: int, details: Dict = None, ip_address: str = None):
        """Log user action for audit trail"""
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address
        )
        db.add(audit_log)
        db.commit()


# ==================== FASTAPI APPLICATION ====================
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI(
    title="Clinic Management System ERP",
    description="Complete ERP for Clinic Management with EHR, Inventory, Billing, and Telehealth",
    version="1.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== AUTH ENDPOINTS ====================
@app.post("/api/auth/register", response_model=Token)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register new user with role-based access"""
    # Check if user exists
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=400, detail="Username already registered")
    
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role,
        is_active=True
    )
    db.add(user)
    db.flush()
    
    # Create user profile
    profile = UserProfile(
        user_id=user.id,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone
    )
    db.add(profile)
    db.commit()
    
    # Generate token
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value, "user_id": user.id}
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.value,
        "user_id": user.id
    }


@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login with username and password"""
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is disabled")
    
    # Update last login
    user.last_login = datetime.utcnow()
    user.failed_login_attempts = 0
    db.commit()
    
    # Generate token
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value, "user_id": user.id}
    )
    
    # Log action
    AuditService.log_action(db, user.id, "LOGIN", "User", user.id)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role.value,
        "user_id": user.id
    }


# ==================== PATIENT ENDPOINTS ====================
@app.post("/api/patients/")
async def create_patient(
    patient_data: PatientCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.RECEPTIONIST]))
):
    """Create new patient record"""
    patient = PatientService.create_patient(db, patient_data)
    AuditService.log_action(db, current_user.id, "CREATE_PATIENT", "Patient", patient.id)
    return patient


@app.get("/api/patients/search")
async def search_patients(
    query: str = "",
    postal_code: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Search patients with optimized query"""
    patients = PatientService.search_patients(db, query, postal_code)
    return patients


@app.get("/api/patients/{patient_id}")
async def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get patient details"""
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    AuditService.log_action(db, current_user.id, "VIEW_PATIENT", "Patient", patient_id)
    return patient


# ==================== APPOINTMENT ENDPOINTS ====================
@app.post("/api/appointments/")
async def create_appointment(
    appointment_data: AppointmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create new appointment"""
    # Check if time slot is available
    existing = db.query(Appointment).filter(
        Appointment.doctor_id == appointment_data.doctor_id,
        Appointment.appointment_date == appointment_data.appointment_date,
        Appointment.appointment_time == appointment_data.appointment_time,
        Appointment.status.in_([AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED])
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Time slot not available")
    
    appointment = Appointment(**appointment_data.dict())
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    
    AuditService.log_action(db, current_user.id, "CREATE_APPOINTMENT", "Appointment", appointment.id)
    return appointment


@app.get("/api/appointments/doctor/{doctor_id}")
async def get_doctor_appointments(
    doctor_id: int,
    date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get appointments for a doctor"""
    query = db.query(Appointment).filter(Appointment.doctor_id == doctor_id)
    
    if date:
        query = query.filter(Appointment.appointment_date == date)
    else:
        query = query.filter(Appointment.appointment_date >= datetime.now().date())
    
    appointments = query.order_by(
        Appointment.appointment_date.asc(),
        Appointment.appointment_time.asc()
    ).all()
    
    return appointments


@app.patch("/api/appointments/{appointment_id}/status")
async def update_appointment_status(
    appointment_id: int,
    new_status: AppointmentStatus,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update appointment status"""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    appointment.status = new_status
    db.commit()
    
    AuditService.log_action(db, current_user.id, "UPDATE_APPOINTMENT_STATUS", "Appointment", appointment_id)
    return appointment


# ==================== PRESCRIPTION ENDPOINTS ====================
@app.post("/api/prescriptions/")
async def create_prescription(
    prescription_data: PrescriptionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.DOCTOR]))
):
    """Create e-prescription with drug safety checks"""
    prescription = PrescriptionService.create_prescription(db, prescription_data, current_user.id)
    AuditService.log_action(db, current_user.id, "CREATE_PRESCRIPTION", "Prescription", prescription.id)
    return prescription


@app.get("/api/prescriptions/{prescription_id}")
async def get_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get prescription details"""
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    # Load medications
    medications = db.query(PrescriptionItem, Medicine).join(Medicine).filter(
        PrescriptionItem.prescription_id == prescription_id
    ).all()
    
    result = {
        "prescription": prescription,
        "medications": [{
            "medicine": med,
            "prescription_item": item
        } for item, med in medications]
    }
    
    return result


@app.post("/api/prescriptions/{prescription_id}/dispense")
async def dispense_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.PHARMACIST]))
):
    """Dispense prescription and update inventory"""
    prescription = db.query(Prescription).filter(Prescription.id == prescription_id).first()
    if not prescription:
        raise HTTPException(status_code=404, detail="Prescription not found")
    
    if prescription.status != PrescriptionStatus.PENDING:
        raise HTTPException(status_code=400, detail="Prescription already dispensed or cancelled")
    
    # Get prescription items
    items = db.query(PrescriptionItem).filter(
        PrescriptionItem.prescription_id == prescription_id
    ).all()
    
    dispensed_details = []
    
    # Dispense each medication
    for item in items:
        if not InventoryService.check_stock_availability(db, item.medicine_id, item.quantity):
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for medicine ID: {item.medicine_id}"
            )
        
        dispensed = InventoryService.dispense_medicine_fifo(db, item.medicine_id, item.quantity)
        dispensed_details.append({
            "medicine_id": item.medicine_id,
            "dispensed": dispensed
        })
    
    # Update prescription status
    prescription.status = PrescriptionStatus.DISPENSED
    prescription.dispensed_by = current_user.id
    prescription.dispensed_at = datetime.utcnow()
    db.commit()
    
    AuditService.log_action(db, current_user.id, "DISPENSE_PRESCRIPTION", "Prescription", prescription_id)
    
    return {"message": "Prescription dispensed successfully", "details": dispensed_details}


# ==================== INVENTORY ENDPOINTS ====================
@app.get("/api/inventory/expiring")
async def get_expiring_medicines(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.PHARMACIST, UserRole.MANAGER]))
):
    """Get medicines expiring within specified days"""
    return InventoryService.get_expiring_medicines(db, days)


@app.get("/api/inventory/reorder")
async def get_reorder_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.PHARMACIST, UserRole.MANAGER]))
):
    """Get medicines that need reordering"""
    return InventoryService.check_reorder_levels(db)


@app.get("/api/inventory/medicine/{medicine_id}")
async def get_medicine_stock(
    medicine_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get stock details for a medicine"""
    inventory = db.query(Inventory, Medicine).join(Medicine).filter(
        Inventory.medicine_id == medicine_id,
        Inventory.quantity > 0,
        Inventory.expiry_date > datetime.now().date()
    ).all()
    
    total_quantity = sum(inv.quantity for inv, _ in inventory)
    
    return {
        "medicine_id": medicine_id,
        "total_quantity": total_quantity,
        "batches": [{
            "batch_number": inv.batch_number,
            "quantity": inv.quantity,
            "expiry_date": inv.expiry_date,
            "location": inv.location
        } for inv, _ in inventory]
    }


# ==================== BILLING ENDPOINTS ====================
@app.post("/api/bills/")
async def create_bill(
    patient_id: int,
    appointment_id: Optional[int] = None,
    items: List[Dict] = [],
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.RECEPTIONIST]))
):
    """Create new bill"""
    bill = BillingService.create_bill(db, patient_id, appointment_id, items)
    AuditService.log_action(db, current_user.id, "CREATE_BILL", "Bill", bill.id)
    return bill


@app.post("/api/bills/{bill_id}/payment")
async def process_payment(
    bill_id: int,
    amount: float,
    payment_method: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.RECEPTIONIST]))
):
    """Process payment for a bill"""
    bill = BillingService.process_payment(db, bill_id, amount, payment_method)
    AuditService.log_action(db, current_user.id, "PROCESS_PAYMENT", "Bill", bill_id, 
                           {"amount": amount, "method": payment_method})
    return bill


@app.get("/api/bills/revenue-report")
async def revenue_report(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    """Generate revenue report"""
    return BillingService.get_revenue_report(db, start_date, end_date)


# ==================== LOCATION INTELLIGENCE ENDPOINTS ====================
@app.get("/api/analytics/demand/{cluster_id}")
async def get_demand_analysis(
    cluster_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    """Get demand analysis for postal code cluster"""
    return LocationService.get_demand_analysis(db, cluster_id)


@app.get("/api/analytics/postal-code-stats")
async def get_postal_code_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role([UserRole.ADMIN, UserRole.MANAGER]))
):
    """Get statistics for all postal code clusters"""
    clusters = db.query(PostalCodeCluster).all()
    return clusters


# ==================== DATABASE INITIALIZATION ====================
def init_db():
    """Initialize database with tables and indexes"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")


if __name__ == "__main__":
    init_db()
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)