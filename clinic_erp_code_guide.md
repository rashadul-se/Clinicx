# 🏥 Clinic ERP - Code Architecture Quick Reference

## 📊 Summary Table

| Part | File | Purpose | Key Components | Lines of Code |
|------|------|---------|----------------|---------------|
| **Part 1** | `clinic_erp_part1.py` | Database Models & Core Classes | 15+ database models, security utilities, validators | ~560 |
| **Part 2** | `clinic_erp_part2.py` | FastAPI Microservices | REST API endpoints, authentication, business logic | ~1000 |
| **Part 3** | `clinic_erp_part3.py` | Streamlit Frontend | User interface, dashboards, forms | ~800 |
| **Part 4** | `clinic_erp_part4.py` | Additional Services | Drug checker, notifications, optimizations | ~600 |
| **Part 5** | `clinic_erp_part5.py` | Deployment & Config | Docker, Nginx, Celery, documentation | ~400+ |

---

## 📁 Part 1: Database Models (`clinic_erp_part1.py`)

### **What It Does**
Foundation layer - defines all data structures and security

### **Key Components**

| Component | Purpose | Example |
|-----------|---------|---------|
| **User Model** | Store login credentials, roles, MFA settings | `username`, `password_hash`, `role`, `mfa_enabled` |
| **Patient Model** | Complete patient demographics & medical info | `pid`, `name`, `postal_code`, `allergies`, `insurance` |
| **Doctor Model** | Doctor profiles, credentials, fees | `license_number`, `specialty`, `consultation_fee` |
| **Appointment Model** | Schedule appointments (in-person/teleconsult) | `date`, `time`, `type`, `video_room_id`, `status` |
| **Prescription Model** | E-prescriptions with multiple medicines | `diagnosis`, `medicines`, `status`, `valid_until` |
| **Medicine Model** | Medicine catalog with pricing | `name`, `generic_name`, `price`, `reorder_level` |
| **MedicineStock Model** | Inventory by batch & expiry (FIFO) | `batch_number`, `expiry_date`, `quantity`, `location` |
| **AuditLog Model** | Track all system actions (compliance) | `user_id`, `action`, `resource`, `timestamp`, `ip` |
| **PostalCodeCluster** | Location intelligence analytics | `postal_code`, `patient_count`, `specialty_demand` |
| **SecurityManager** | Password hashing & verification | `hash_password()`, `verify_password()`, `generate_salt()` |

### **Usage in Other Parts**
```python
# Part 2, 3, 4 import and use these models
from clinic_erp_part1 import Patient, User, SecurityManager

# Create patient
patient = Patient(pid="PID001", first_name="John", ...)
db.add(patient)
```

---

## 🚀 Part 2: FastAPI API Server (`clinic_erp_part2.py`)

### **What It Does**
Backend server - handles all business logic and data operations

### **Key Endpoints**

| Endpoint | Method | Purpose | Who Can Access |
|----------|--------|---------|----------------|
| `/api/auth/login` | POST | User login, returns JWT token | Everyone |
| `/api/auth/register` | POST | Create new user account | Admin only |
| `/api/patients` | POST | Register new patient | Admin, Receptionist, Doctor |
| `/api/patients/search` | GET | Search patients by name/PID/phone | Admin, Doctor, Nurse |
| `/api/patients/{id}` | GET | Get patient details | Admin, Doctor, Nurse |
| `/api/appointments` | POST | Book appointment | Admin, Receptionist, Patient |
| `/api/appointments/doctor/{id}` | GET | Get doctor's appointments | Admin, Doctor |
| `/api/prescriptions` | POST | Create e-prescription | Doctor only |
| `/api/prescriptions/{id}` | GET | View prescription | Doctor, Pharmacist, Patient (own) |
| `/api/inventory/medicines` | GET | List medicines with stock | Admin, Pharmacist, Doctor |
| `/api/inventory/expiring` | GET | Medicines expiring soon | Admin, Pharmacist |
| `/api/analytics/postal-clusters` | GET | Patient distribution by postal code | Admin, Manager |
| `/api/analytics/appointments-stats` | GET | Appointment statistics | Admin, Manager |

### **Key Services**

| Service | Purpose | Example |
|---------|---------|---------|
| **AuthService** | JWT token generation & verification | `create_access_token()`, `verify_token()`, `check_permission()` |
| **AuditService** | Log all actions for compliance | `log_action(user_id, "VIEW_PATIENT", ...)` |
| **Database Session** | Manage DB connections efficiently | `get_db()` dependency injection |

### **Security Features**

| Feature | Implementation |
|---------|----------------|
| **Authentication** | JWT tokens with 60-min expiry |
| **Authorization** | Role-based access control (RBAC) |
| **Account Lockout** | Lock after 5 failed login attempts for 30 min |
| **Password Security** | PBKDF2-SHA256 with 100k iterations |
| **Audit Logging** | Every action logged with user, IP, timestamp |
| **Input Validation** | Pydantic models validate all inputs |

### **How It Works**
```python
# Frontend makes HTTP request
POST /api/auth/login
{
  "username": "doctor1",
  "password": "password123"
}

# API responds with token
{
  "access_token": "eyJhbGc...",
  "user": {"id": 1, "role": "doctor"}
}

# Frontend uses token in subsequent requests
GET /api/patients/123
Headers: {"Authorization": "Bearer eyJhbGc..."}
```

---

## 🖥️ Part 3: Streamlit Frontend (`clinic_erp_part3.py`)

### **What It Does**
User interface - what clinic staff see and interact with

### **Main Pages**

| Page | Who Sees It | Features |
|------|------------|----------|
| **Login** | Everyone | Username/password form, MFA support |
| **Dashboard** | All authenticated users | KPI cards, charts, quick stats |
| **Patients** | Admin, Doctor, Nurse, Receptionist | Search, register, view patient details |
| **Appointments** | Admin, Doctor, Nurse, Receptionist | View calendar, book appointments |
| **Prescriptions** | Doctor, Pharmacist | Create e-prescriptions, view history |
| **Inventory** | Admin, Pharmacist | Stock levels, expiring items, reorder alerts |
| **Analytics** | Admin, Manager | Demographics, financials, location intelligence |
| **Teleconsultation** | Doctor | Video consultation interface |

### **Key Features**

| Feature | Implementation | Benefit |
|---------|----------------|---------|
| **Role-Based UI** | Different menus per role | Users only see relevant features |
| **Session Management** | `st.session_state` stores token & user | Stays logged in across pages |
| **API Client** | `APIClient` class wraps all API calls | Simplified HTTP requests |
| **Real-Time Search** | Instant patient/medicine search | Fast lookup without page reload |
| **Interactive Charts** | Plotly visualizations | Click, zoom, hover for insights |
| **Form Validation** | Client-side checks before API call | Better UX, faster feedback |

### **User Flow Example**
```
1. User opens http://localhost:8501
2. Sees login page → enters credentials
3. Frontend calls API: POST /api/auth/login
4. API returns token → stored in session
5. Page reloads → shows dashboard
6. User clicks "Patients" → navigates to patient page
7. User searches "John" → calls GET /api/patients/search?query=John
8. Results displayed in table
```

---

## 🔧 Part 4: Additional Services (`clinic_erp_part4.py`)

### **What It Does**
Advanced features that enhance the core system

### **Key Services**

| Service | Purpose | Key Methods |
|---------|---------|-------------|
| **DatabaseOptimizer** | Create indexes for fast queries | `create_indexes()`, `analyze_tables()` |
| **DrugInteractionChecker** | Check drug-drug & drug-allergy conflicts | `check_interactions()`, `check_allergies()` |
| **NotificationService** | Send emails, SMS, WhatsApp | `send_email()`, `send_sms()`, `send_whatsapp()` |
| **AppointmentReminderService** | Automated appointment reminders | `send_reminders()`, `send_followup_reminders()` |
| **InventoryManager** | FIFO dispensing, expiry tracking | `dispense_medicine_fifo()`, `get_expiring_items()` |
| **BackgroundTaskScheduler** | Run daily maintenance tasks | `run_daily_tasks()` |
| **InputValidator** | Validate phone, postal codes, dates | `validate_phone()`, `sanitize_input()` |

### **Drug Interaction Checker**

| Feature | How It Works |
|---------|-------------|
| **Drug-Drug Interactions** | Checks new medicine against patient's existing meds |
| **Drug-Allergy Alerts** | Compares medicine against patient allergies |
| **Cross-Allergy Detection** | Detects related allergies (e.g., penicillin group) |
| **Recommendations** | Returns warnings and alternative suggestions |

**Example**:
```python
# Patient on warfarin (blood thinner)
# Doctor prescribes aspirin
checker = DrugInteractionChecker()
interactions = checker.check_interactions(
    new_medicines=["aspirin"],
    existing_medicines=["warfarin"]
)
# Returns: {"aspirin": ["warfarin"]}
# Warning: Bleeding risk!
```

### **Notification Service**

| Channel | Use Case | Implementation |
|---------|----------|----------------|
| **Email** | Appointment reminders, reports | SMTP (Gmail, SendGrid) |
| **SMS** | Urgent reminders, OTP codes | Twilio API |
| **WhatsApp** | Rich messages with links | WhatsApp Business API |

### **Inventory FIFO Logic**

| Step | Action |
|------|--------|
| 1. **Query** | Get all batches for medicine, ordered by expiry date |
| 2. **Filter** | Exclude expired batches |
| 3. **Dispense** | Take from oldest batch first |
| 4. **Update** | Reduce quantity in database |
| 5. **Track** | Log which batch was dispensed |

**Example**:
```
Medicine: Paracetamol 500mg
Stock:
  - Batch A: 100 tablets, expires 2025-01-15
  - Batch B: 200 tablets, expires 2025-03-20
  - Batch C: 150 tablets, expires 2025-05-10

Dispense 120 tablets:
  - Take 100 from Batch A (oldest)
  - Take 20 from Batch B
  - Batch C untouched (will be used later)
```

---

## 🚢 Part 5: Deployment (`clinic_erp_part5.py`)

### **What It Does**
Production deployment configuration and documentation

### **Configuration Files**

| File | Purpose |
|------|---------|
| **docker-compose.yml** | Orchestrates all services (API, DB, Redis, Frontend, Celery) |
| **Dockerfile.api** | Builds FastAPI container |
| **Dockerfile.streamlit** | Builds Streamlit container |
| **nginx.conf** | Reverse proxy, SSL, rate limiting |
| **.env** | Environment variables (passwords, keys) |
| **requirements.txt** | Python dependencies |
| **init.sql** | Database initialization scripts |
| **tasks.py** | Celery background tasks |

### **Services Architecture**

| Service | Purpose | Port | Dependencies |
|---------|---------|------|--------------|
| **postgres** | Database | 5432 | None |
| **redis** | Cache & task queue | 6379 | None |
| **api** | FastAPI backend | 8000 | postgres, redis |
| **frontend** | Streamlit UI | 8501 | api |
| **celery_worker** | Background tasks | - | postgres, redis |
| **celery_beat** | Scheduled tasks | - | postgres, redis |
| **nginx** | Reverse proxy | 80, 443 | api, frontend |

### **Background Tasks (Celery)**

| Task | Schedule | Purpose |
|------|----------|---------|
| **send_appointment_reminders** | Daily at 9 AM | SMS/email reminders 24h before appointment |
| **check_expiring_medicines** | Daily at 8 AM | Alert pharmacist about expiring stock |
| **generate_reorder_list** | Monday at 10 AM | Create purchase orders for low stock |
| **backup_database** | Daily at 2 AM | Automated database backup |

### **Deployment Commands**

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# Run database migrations
docker-compose exec api alembic upgrade head

# Create admin user
docker-compose exec api python create_admin.py
```

---

## 🔄 How All Parts Work Together

### **Complete Request Flow**

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Browser   │ ─────▶  │  Streamlit  │ ─────▶  │   FastAPI   │ ─────▶  │ PostgreSQL  │
│  (Part 3)   │         │  Frontend   │         │   Backend   │         │  Database   │
│             │         │  (Part 3)   │         │  (Part 2)   │         │  (Part 1)   │
└─────────────┘         └─────────────┘         └─────────────┘         └─────────────┘
      │                        │                        │                        │
      │                        │                        ▼                        │
      │                        │                 ┌─────────────┐                │
      │                        │                 │   Redis     │                │
      │                        │                 │   Cache     │                │
      │                        │                 └─────────────┘                │
      │                        │                        │                        │
      │                        │                        ▼                        │
      │                        │                 ┌─────────────┐                │
      │                        │                 │   Celery    │                │
      │                        │                 │   Worker    │                │
      │                        │                 │  (Part 4)   │                │
      │                        │                 └─────────────┘                │
      │                        │                        │                        │
      └────────────────────────┴────────────────────────┴────────────────────────┘
                               Background Tasks (Reminders, Backups, etc.)
```

### **Example: Booking an Appointment**

| Step | Part | Action |
|------|------|--------|
| 1 | Part 3 (Frontend) | User fills appointment form |
| 2 | Part 3 (Frontend) | Validates input (date, time format) |
| 3 | Part 3 (Frontend) | Calls `APIClient.post("appointments", data)` |
| 4 | Part 2 (API) | Receives POST /api/appointments |
| 5 | Part 2 (API) | Verifies JWT token → gets user from Part 1 |
| 6 | Part 2 (API) | Checks permissions (is user receptionist/admin?) |
| 7 | Part 2 (API) | Queries Part 1 database for conflicts |
| 8 | Part 2 (API) | Creates Appointment object from Part 1 |
| 9 | Part 2 (API) | Saves to database |
| 10 | Part 2 (API) | Logs action to AuditLog (Part 1) |
| 11 | Part 4 (Services) | Schedules reminder via Celery |
| 12 | Part 2 (API) | Returns appointment data to Part 3 |
| 13 | Part 3 (Frontend) | Shows success message to user |
| 14 | Part 4 (Celery) | 24h before: sends SMS/email reminder |

### **Example: E-Prescription with Drug Check**

| Step | Part | Action |
|------|------|--------|
| 1 | Part 3 | Doctor enters prescription |
| 2 | Part 3 | Calls `POST /api/prescriptions` |
| 3 | Part 2 | Verifies user is doctor |
| 4 | Part 2 | Gets patient allergies from Part 1 |
| 5 | Part 4 | **DrugInteractionChecker** checks new meds vs existing |
| 6 | Part 4 | **DrugInteractionChecker** checks allergies |
| 7 | Part 2 | If interactions found → returns warning |
| 8 | Part 3 | Shows warning to doctor with continue/cancel options |
| 9 | Part 2 | If confirmed → saves prescription to Part 1 |
| 10 | Part 2 | Updates pharmacy queue |
| 11 | Part 4 | Sends notification to pharmacy |
| 12 | Part 3 | Shows success + prescription ID |

---

## 💡 Key Design Patterns Used

| Pattern | Where | Purpose |
|---------|-------|---------|
| **MVC Architecture** | Parts 1, 2, 3 | Separates data (Part 1), logic (Part 2), UI (Part 3) |
| **Dependency Injection** | Part 2 | `Depends(get_db)` provides DB session to endpoints |
| **Repository Pattern** | Part 2 | Database operations wrapped in services |
| **Decorator Pattern** | Part 2 | `@check_permission()` wraps endpoints for auth |
| **Factory Pattern** | Part 1 | Pydantic models create validated objects |
| **Observer Pattern** | Part 4 | Celery tasks react to database events |
| **Singleton Pattern** | Part 2 | Single database engine shared across app |

---

## 📈 Performance Optimizations

| Optimization | Where | Impact |
|--------------|-------|--------|
| **Database Indexes** | Part 1, 4 | 10-100x faster queries |
| **Connection Pooling** | Part 2 | Reuse DB connections (no reconnect overhead) |
| **Query Result Caching** | Part 2 | Redis caches frequent queries |
| **Async Operations** | Part 2 | Non-blocking I/O for better concurrency |
| **Background Tasks** | Part 4 | Offload slow operations (email sending) |
| **Materialized Views** | Part 5 | Pre-computed analytics |
| **FIFO Algorithm** | Part 4 | Efficient inventory dispensing |

---

## 🔒 Security Layers

| Layer | Implementation | Prevents |
|-------|----------------|----------|
| **Authentication** | JWT tokens (Part 2) | Unauthorized access |
| **Authorization** | RBAC (Part 2) | Privilege escalation |
| **Password Security** | PBKDF2 hashing (Part 1) | Password cracking |
| **Input Validation** | Pydantic (Part 1) + Sanitization (Part 4) | SQL injection, XSS |
| **Audit Logging** | AuditLog (Part 1) | Covers tracks, forensics |
| **Rate Limiting** | Nginx (Part 5) | DDoS attacks |
| **HTTPS/TLS** | Nginx (Part 5) | Man-in-the-middle attacks |
| **Account Lockout** | Part 2 | Brute force attacks |

---

## 🎯 Quick Reference: Who Uses What

| User Role | Main Parts Used | Key Features |
|-----------|----------------|--------------|
| **Admin** | All parts | Full system access, user management, analytics |
| **Doctor** | Parts 2, 3, 4 | Patients, appointments, prescriptions, teleconsult |
| **Nurse** | Parts 2, 3 | View patients, update vitals, assist doctors |
| **Pharmacist** | Parts 2, 3, 4 | Inventory, dispense prescriptions, expiry alerts |
| **Receptionist** | Parts 2, 3 | Register patients, book appointments |
| **Manager** | Parts 2, 3 | Analytics, reports, location intelligence |
| **Patient** | Part 3 (portal) | Book appointments, view records, teleconsult |

---

## 📚 File Dependencies

```
clinic_erp_part1.py (Models & Security)
    ↓
clinic_erp_part2.py (API Server)
    ↓ ↑ (imports Part 1)
clinic_erp_part3.py (Frontend)
    ↓ (calls Part 2 API)
clinic_erp_part4.py (Services)
    ↓ (imports Part 1 & 2)
clinic_erp_part5.py (Deployment)
    → (orchestrates all above)
```

---

## 🚀 Getting Started (Quick Commands)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
export DATABASE_URL="postgresql://user:pass@localhost/clinic_erp"
export SECRET_KEY="your-secret-key-here"

# 3. Initialize database
python -c "from clinic_erp_part1 import Base, engine; Base.metadata.create_all(engine)"

# 4. Start API server (Part 2)
uvicorn clinic_erp_part2:app --reload --port 8000

# 5. Start frontend (Part 3) - in another terminal
streamlit run clinic_erp_part3.py

# 6. Access system
# API: http://localhost:8000/docs
# Frontend: http://localhost:8501
```

---

## 📊 System Statistics

| Metric | Value |
|--------|-------|
| **Total Lines of Code** | ~3,360 |
| **Database Tables** | 15+ |
| **API Endpoints** | 30+ |
| **User Roles** | 7 |
| **Frontend Pages** | 8 |
| **Background Tasks** | 4 |
| **Security Features** | 10+ |
| **Supported Languages** | Python, SQL, JavaScript |

---

**Built with modern best practices for production healthcare applications!** 🏥✨
