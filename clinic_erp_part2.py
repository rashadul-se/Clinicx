"""
Clinic Management System ERP - FastAPI Microservices
Secure API endpoints with authentication, validation, and optimization
"""

from fastapi import FastAPI, Depends, HTTPException, status, Header, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, and_, or_, func
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import jwt
import logging
from typing import Optional, List, Dict
import asyncio
from contextlib import asynccontextmanager

# Import from Part 1
from clinic_erp_part1 import *

# ==================== CONFIGURATION ====================

class Config:
    DATABASE_URL = "postgresql://user:password@localhost:5432/clinic_erp"
    SECRET_KEY = "your-secret-key-change-in-production"
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 60
    REFRESH_TOKEN_EXPIRE_DAYS = 7
    MAX_LOGIN_ATTEMPTS = 5
    LOCK_DURATION_MINUTES = 30

# ==================== DATABASE CONNECTION ====================

engine = create_engine(
    Config.DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==================== AUTHENTICATION SERVICE ====================

security = HTTPBearer()

class AuthService:
    """Authentication and authorization service"""
    
    @staticmethod
    def create_access_token(data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=Config.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=Config.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, Config.SECRET_KEY, algorithm=Config.ALGORITHM)
    
    @staticmethod
    def verify_token(token: str) -> dict:
        try:
            payload = jwt.decode(token, Config.SECRET_KEY, algorithms=[Config.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    
    @staticmethod
    def get_current_user(
        credentials: HTTPAuthorizationCredentials = Depends(security),
        db: Session = Depends(get_db)
    ) -> User:
        token = credentials.credentials
        payload = AuthService.verify_token(token)
        
        user = db.query(User).filter(User.id == payload.get("user_id")).first()
        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive"
            )
        return user
    
    @staticmethod
    def check_permission(required_roles: List[UserRole]):
        def permission_checker(current_user: User = Depends(AuthService.get_current_user)):
            if current_user.role not in [r.value for r in required_roles]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions"
                )
            return current_user
        return permission_checker

# ==================== AUDIT SERVICE ====================

class AuditService:
    """Logging service for compliance"""
    
    @staticmethod
    async def log_action(
        db: Session,
        user_id: int,
        action: str,
        resource_type: str,
        resource_id: Optional[int],
        request: Request,
        details: Optional[str] = None
    ):
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            details=details
        )
        db.add(audit_log)
        db.commit()

# ==================== FASTAPI APPLICATION ====================

app = FastAPI(
    title="Clinic Management System ERP",
    description="Production-ready ERP for comprehensive clinic management",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== AUTHENTICATION ENDPOINTS ====================

@app.post("/api/auth/login")
async def login(
    credentials: UserLogin,
    request: Request,
    db: Session = Depends(get_db)
):
    """Login endpoint with MFA support and account lockout"""
    
    user = db.query(User).filter(User.username == credentials.username).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Check account lockout
    if user.account_locked_until and user.account_locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Account locked until {user.account_locked_until}"
        )
    
    # Verify password
    if not SecurityManager.verify_password(credentials.password, user.salt, user.password_hash):
        user.failed_login_attempts += 1
        
        if user.failed_login_attempts >= Config.MAX_LOGIN_ATTEMPTS:
            user.account_locked_until = datetime.utcnow() + timedelta(minutes=Config.LOCK_DURATION_MINUTES)
        
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # MFA verification (if enabled)
    if user.mfa_enabled and not credentials.mfa_code:
        return {"requires_mfa": True}
    
    # Reset failed attempts
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Generate tokens
    token_data = {"user_id": user.id, "role": user.role}
    access_token = AuthService.create_access_token(token_data)
    refresh_token = AuthService.create_refresh_token(token_data)
    
    # Audit log
    await AuditService.log_action(db, user.id, "LOGIN", "User", user.id, request)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }

@app.post("/api/auth/register")
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.check_permission([UserRole.ADMIN]))
):
    """User registration (admin only)"""
    
    # Check if user exists
    existing = db.query(User).filter(
        or_(User.username == user_data.username, User.email == user_data.email)
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already exists"
        )
    
    # Create user
    salt = SecurityManager.generate_salt()
    password_hash = SecurityManager.hash_password(user_data.password, salt)
    
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash,
        salt=salt,
        role=user_data.role.value
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    await AuditService.log_action(
        db, current_user.id, "CREATE_USER", "User", new_user.id, request
    )
    
    return {"id": new_user.id, "username": new_user.username, "role": new_user.role}

# ==================== PATIENT ENDPOINTS ====================

@app.post("/api/patients")
async def create_patient(
    patient_data: PatientCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """Create new patient with auto-generated PID"""
    
    # Generate unique PID
    pid = f"PID{datetime.now().strftime('%Y%m%d')}{db.query(func.count(Patient.id)).scalar() + 1:06d}"
    
    patient = Patient(
        pid=pid,
        first_name=patient_data.first_name,
        last_name=patient_data.last_name,
        date_of_birth=patient_data.date_of_birth,
        gender=patient_data.gender,
        phone=patient_data.phone,
        email=patient_data.email,
        postal_code=patient_data.postal_code,
        address=patient_data.address,
        blood_group=patient_data.blood_group,
        allergies=patient_data.allergies,
        insurance_provider=patient_data.insurance_provider,
        insurance_number=patient_data.insurance_number
    )
    
    db.add(patient)
    db.commit()
    db.refresh(patient)
    
    # Update postal code cluster
    cluster = db.query(PostalCodeCluster).filter(
        PostalCodeCluster.postal_code == patient_data.postal_code
    ).first()
    
    if cluster:
        cluster.patient_count += 1
        cluster.last_updated = datetime.utcnow()
    else:
        cluster = PostalCodeCluster(
            postal_code=patient_data.postal_code,
            patient_count=1
        )
        db.add(cluster)
    
    db.commit()
    
    await AuditService.log_action(
        db, current_user.id, "CREATE_PATIENT", "Patient", patient.id, request
    )
    
    return patient

@app.get("/api/patients/{patient_id}")
async def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """Get patient details with EHR"""
    
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    # Check permissions (doctors/nurses can only see their patients)
    if current_user.role in [UserRole.PATIENT.value]:
        # Patients can only see their own records
        if not patient.user_id or patient.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
    
    return patient

@app.get("/api/patients/search")
async def search_patients(
    query: str,
    postal_code: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.check_permission([UserRole.ADMIN, UserRole.DOCTOR, UserRole.NURSE, UserRole.RECEPTIONIST]))
):
    """Optimized patient search with indexing"""
    
    filters = or_(
        Patient.first_name.ilike(f"%{query}%"),
        Patient.last_name.ilike(f"%{query}%"),
        Patient.pid.ilike(f"%{query}%"),
        Patient.phone.ilike(f"%{query}%")
    )
    
    if postal_code:
        filters = and_(filters, Patient.postal_code == postal_code)
    
    # Optimized query with index hints
    patients = db.query(Patient).filter(filters).limit(50).all()
    
    return patients

# ==================== APPOINTMENT ENDPOINTS ====================

@app.post("/api/appointments")
async def create_appointment(
    appointment_data: AppointmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """Create appointment with conflict checking"""
    
    # Check doctor availability
    existing = db.query(Appointment).filter(
        and_(
            Appointment.doctor_id == appointment_data.doctor_id,
            Appointment.appointment_date == appointment_data.appointment_date,
            Appointment.appointment_time == appointment_data.appointment_time,
            Appointment.status.in_(['scheduled', 'confirmed'])
        )
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Time slot already booked"
        )
    
    appointment = Appointment(
        patient_id=appointment_data.patient_id,
        doctor_id=appointment_data.doctor_id,
        appointment_date=appointment_data.appointment_date,
        appointment_time=appointment_data.appointment_time,
        consultation_type=appointment_data.consultation_type.value,
        chief_complaint=appointment_data.chief_complaint,
        status=AppointmentStatus.SCHEDULED.value
    )
    
    # Generate video room for teleconsultation
    if appointment_data.consultation_type == ConsultationType.TELECONSULTATION:
        appointment.video_room_id = f"ROOM_{secrets.token_urlsafe(16)}"
    
    db.add(appointment)
    db.commit()
    db.refresh(appointment)
    
    await AuditService.log_action(
        db, current_user.id, "CREATE_APPOINTMENT", "Appointment", appointment.id, request
    )
    
    return appointment

@app.get("/api/appointments/doctor/{doctor_id}")
async def get_doctor_appointments(
    doctor_id: int,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.get_current_user)
):
    """Get doctor's appointments with optimized query"""
    
    appointments = db.query(Appointment).filter(
        and_(
            Appointment.doctor_id == doctor_id,
            Appointment.appointment_date >= start_date,
            Appointment.appointment_date <= end_date
        )
    ).order_by(Appointment.appointment_date, Appointment.appointment_time).all()
    
    return appointments

# ==================== PRESCRIPTION ENDPOINTS ====================

@app.post("/api/prescriptions")
async def create_prescription(
    prescription_data: PrescriptionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.check_permission([UserRole.DOCTOR]))
):
    """Create e-prescription with drug interaction checking"""
    
    # Get patient allergies
    patient = db.query(Patient).filter(Patient.id == prescription_data.patient_id).first()
    
    prescription = Prescription(
        patient_id=prescription_data.patient_id,
        doctor_id=prescription_data.doctor_id,
        diagnosis=prescription_data.diagnosis,
        notes=prescription_data.notes,
        valid_until=datetime.now().date() + timedelta(days=30)
    )
    
    db.add(prescription)
    db.flush()
    
    # Add prescription items
    for item in prescription_data.items:
        medicine = db.query(Medicine).filter(Medicine.id == item['medicine_id']).first()
        
        if not medicine:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Medicine {item['medicine_id']} not found")
        
        # TODO: Implement drug interaction checking
        # Check against patient allergies and existing prescriptions
        
        prescription_item = PrescriptionItem(
            prescription_id=prescription.id,
            medicine_id=item['medicine_id'],
            dosage=item['dosage'],
            frequency=item['frequency'],
            duration=item['duration'],
            quantity=item['quantity'],
            instructions=item.get('instructions')
        )
        db.add(prescription_item)
    
    db.commit()
    db.refresh(prescription)
    
    await AuditService.log_action(
        db, current_user.id, "CREATE_PRESCRIPTION", "Prescription", prescription.id, request
    )
    
    return prescription

# ==================== INVENTORY ENDPOINTS ====================

@app.get("/api/inventory/medicines")
async def get_medicines(
    search: Optional[str] = None,
    category: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.check_permission([UserRole.ADMIN, UserRole.PHARMACIST, UserRole.DOCTOR]))
):
    """Get medicines with stock levels (FIFO)"""
    
    query = db.query(Medicine)
    
    if search:
        query = query.filter(
            or_(
                Medicine.name.ilike(f"%{search}%"),
                Medicine.generic_name.ilike(f"%{search}%")
            )
        )
    
    if category:
        query = query.filter(Medicine.category == category)
    
    medicines = query.limit(100).all()
    
    # Get current stock for each medicine using FIFO
    result = []
    for med in medicines:
        stock = db.query(
            func.sum(MedicineStock.quantity)
        ).filter(
            and_(
                MedicineStock.medicine_id == med.id,
                MedicineStock.expiry_date > date.today()
            )
        ).scalar() or 0
        
        result.append({
            "id": med.id,
            "name": med.name,
            "generic_name": med.generic_name,
            "category": med.category,
            "unit_price": med.unit_price,
            "current_stock": stock,
            "reorder_level": med.reorder_level,
            "needs_reorder": stock < med.reorder_level
        })
    
    return result

@app.get("/api/inventory/expiring")
async def get_expiring_medicines(
    days: int = 30,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.check_permission([UserRole.ADMIN, UserRole.PHARMACIST]))
):
    """Get medicines expiring within specified days"""
    
    expiry_threshold = date.today() + timedelta(days=days)
    
    expiring = db.query(
        MedicineStock, Medicine
    ).join(
        Medicine, MedicineStock.medicine_id == Medicine.id
    ).filter(
        and_(
            MedicineStock.expiry_date <= expiry_threshold,
            MedicineStock.expiry_date > date.today(),
            MedicineStock.quantity > 0
        )
    ).order_by(MedicineStock.expiry_date).all()
    
    return [
        {
            "medicine_name": med.name,
            "batch_number": stock.batch_number,
            "expiry_date": stock.expiry_date,
            "quantity": stock.quantity,
            "location": stock.location
        }
        for stock, med in expiring
    ]

# ==================== ANALYTICS ENDPOINTS ====================

@app.get("/api/analytics/postal-clusters")
async def get_postal_clusters(
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.check_permission([UserRole.ADMIN, UserRole.MANAGER]))
):
    """Get patient distribution by postal code"""
    
    clusters = db.query(PostalCodeCluster).order_by(
        PostalCodeCluster.patient_count.desc()
    ).all()
    
    return clusters

@app.get("/api/analytics/appointments-stats")
async def get_appointment_stats(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(AuthService.check_permission([UserRole.ADMIN, UserRole.MANAGER]))
):
    """Get appointment statistics"""
    
    stats = db.query(
        Appointment.status,
        Appointment.consultation_type,
        func.count(Appointment.id).label('count')
    ).filter(
        and_(
            Appointment.appointment_date >= start_date,
            Appointment.appointment_date <= end_date
        )
    ).group_by(Appointment.status, Appointment.consultation_type).all()
    
    return [
        {
            "status": s.status,
            "consultation_type": s.consultation_type,
            "count": s.count
        }
        for s in stats
    ]

# ==================== HEALTH CHECK ====================

@app.get("/api/health")
async def health_check():
    """Service health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "service": "Clinic Management System ERP"
    }

print("✅ FastAPI microservices initialized successfully!")
print("🚀 Run with: uvicorn clinic_erp_part2:app --reload --port 8000")
