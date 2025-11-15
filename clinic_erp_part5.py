"""
Clinic Management System ERP - Deployment Configuration & Documentation
Production deployment, security, monitoring, and usage guide
"""

# ==================== requirements.txt ====================
"""
# Save this as requirements.txt

# Core Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
streamlit==1.28.0

# Database
sqlalchemy==2.0.23
psycopg2-binary==2.9.9
alembic==1.12.1

# Authentication & Security
pyjwt==2.8.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Data Validation
pydantic==2.5.0
email-validator==2.1.0

# API & HTTP
requests==2.31.0
httpx==0.25.1

# Data Processing
pandas==2.1.3
numpy==1.26.2

# Visualization
plotly==5.18.0
matplotlib==3.8.2

# Notifications
twilio==8.10.0
boto3==1.29.7  # For AWS SNS

# Background Tasks
celery==5.3.4
redis==5.0.1

# Monitoring
prometheus-client==0.19.0
sentry-sdk==1.38.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.1

# Development
black==23.11.0
flake8==6.1.0
mypy==1.7.1
"""

# ==================== Docker Compose Configuration ====================
"""
# Save this as docker-compose.yml

version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: clinic_erp_db
    environment:
      POSTGRES_DB: clinic_erp
      POSTGRES_USER: clinic_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - clinic_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U clinic_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis for Caching & Celery
  redis:
    image: redis:7-alpine
    container_name: clinic_erp_redis
    ports:
      - "6379:6379"
    networks:
      - clinic_network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # FastAPI Backend
  api:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: clinic_erp_api
    environment:
      DATABASE_URL: postgresql://clinic_user:${DB_PASSWORD}@postgres:5432/clinic_erp
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      SMTP_PASSWORD: ${SMTP_PASSWORD}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - clinic_network
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped

  # Streamlit Frontend
  frontend:
    build:
      context: .
      dockerfile: Dockerfile.streamlit
    container_name: clinic_erp_frontend
    environment:
      API_BASE_URL: http://api:8000/api
    ports:
      - "8501:8501"
    depends_on:
      - api
    networks:
      - clinic_network
    restart: unless-stopped

  # Celery Worker for Background Tasks
  celery_worker:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: clinic_erp_celery
    command: celery -A tasks worker --loglevel=info
    environment:
      DATABASE_URL: postgresql://clinic_user:${DB_PASSWORD}@postgres:5432/clinic_erp
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    networks:
      - clinic_network
    restart: unless-stopped

  # Celery Beat for Scheduled Tasks
  celery_beat:
    build:
      context: .
      dockerfile: Dockerfile.api
    container_name: clinic_erp_celery_beat
    command: celery -A tasks beat --loglevel=info
    environment:
      DATABASE_URL: postgresql://clinic_user:${DB_PASSWORD}@postgres:5432/clinic_erp
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis
    networks:
      - clinic_network
    restart: unless-stopped

  # Nginx Reverse Proxy
  nginx:
    image: nginx:alpine
    container_name: clinic_erp_nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - api
      - frontend
    networks:
      - clinic_network
    restart: unless-stopped

volumes:
  postgres_data:

networks:
  clinic_network:
    driver: bridge
"""

# ==================== Dockerfile for FastAPI ====================
"""
# Save this as Dockerfile.api

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY clinic_erp_part1.py .
COPY clinic_erp_part2.py .
COPY clinic_erp_part4.py .

# Create non-root user
RUN useradd -m -u 1000 clinic && chown -R clinic:clinic /app
USER clinic

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/api/health || exit 1

# Run application
CMD ["uvicorn", "clinic_erp_part2:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
"""

# ==================== Dockerfile for Streamlit ====================
"""
# Save this as Dockerfile.streamlit

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY clinic_erp_part3.py .

# Create non-root user
RUN useradd -m -u 1000 clinic && chown -R clinic:clinic /app
USER clinic

EXPOSE 8501

CMD ["streamlit", "run", "clinic_erp_part3.py", "--server.port=8501", "--server.address=0.0.0.0"]
"""

# ==================== Environment Variables ====================
"""
# Save this as .env (DO NOT commit to version control)

# Database
DB_PASSWORD=your_secure_password_here

# JWT Secret
SECRET_KEY=your_jwt_secret_key_here_use_random_string

# Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@example.com
SMTP_PASSWORD=your_email_password

# SMS Configuration (Twilio)
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+1234567890

# AWS Configuration (for SNS)
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1

# Sentry (Error Tracking)
SENTRY_DSN=your_sentry_dsn

# Environment
ENVIRONMENT=production
DEBUG=false
"""

# ==================== Nginx Configuration ====================
"""
# Save this as nginx.conf

events {
    worker_connections 1024;
}

http {
    upstream api_backend {
        server api:8000;
    }

    upstream frontend_backend {
        server frontend:8501;
    }

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone=login_limit:10m rate=3r/m;

    server {
        listen 80;
        server_name clinic.example.com;

        # Redirect HTTP to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name clinic.example.com;

        # SSL Configuration
        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;
        ssl_prefer_server_ciphers on;

        # Security Headers
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

        # API Routes
        location /api/ {
            limit_req zone=api_limit burst=20 nodelay;
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Login endpoint with stricter rate limiting
        location /api/auth/login {
            limit_req zone=login_limit burst=5 nodelay;
            proxy_pass http://api_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        }

        # Frontend Routes
        location / {
            proxy_pass http://frontend_backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }

        # Static files caching
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
}
"""

# ==================== Database Migration Script ====================
"""
# Save this as init.sql

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Create custom functions
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables (will be created by SQLAlchemy)
-- These triggers will be created after tables are initialized

-- Create materialized view for analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS patient_statistics AS
SELECT 
    postal_code,
    COUNT(*) as patient_count,
    AVG(EXTRACT(YEAR FROM AGE(date_of_birth))) as avg_age,
    COUNT(*) FILTER (WHERE gender = 'Male') as male_count,
    COUNT(*) FILTER (WHERE gender = 'Female') as female_count
FROM patients
GROUP BY postal_code;

CREATE INDEX ON patient_statistics(postal_code);

-- Function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_patient_statistics()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY patient_statistics;
END;
$$ LANGUAGE plpgsql;
"""

# ==================== Celery Tasks ====================
"""
# Save this as tasks.py

from celery import Celery
from celery.schedules import crontab
import os

# Initialize Celery
app = Celery(
    'clinic_erp_tasks',
    broker=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0')
)

# Configure Celery
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

# Scheduled Tasks
app.conf.beat_schedule = {
    'send-appointment-reminders': {
        'task': 'tasks.send_appointment_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    'check-expiring-medicines': {
        'task': 'tasks.check_expiring_medicines',
        'schedule': crontab(hour=8, minute=0),  # Daily at 8 AM
    },
    'generate-reorder-list': {
        'task': 'tasks.generate_reorder_list',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),  # Monday 10 AM
    },
    'backup-database': {
        'task': 'tasks.backup_database',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}

@app.task(name='tasks.send_appointment_reminders')
def send_appointment_reminders():
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine
    from clinic_erp_part4 import AppointmentReminderService, NotificationService
    
    engine = create_engine(os.getenv('DATABASE_URL'))
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        notifier = NotificationService()
        reminder_service = AppointmentReminderService(db, notifier)
        import asyncio
        asyncio.run(reminder_service.send_reminders())
        return "Reminders sent successfully"
    finally:
        db.close()

@app.task(name='tasks.check_expiring_medicines')
def check_expiring_medicines():
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine
    from clinic_erp_part4 import InventoryManager
    
    engine = create_engine(os.getenv('DATABASE_URL'))
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        inventory = InventoryManager(db)
        expiring = inventory.get_expiring_items(30)
        
        if expiring:
            # Send notification to pharmacy manager
            pass
        
        return f"Found {len(expiring)} expiring items"
    finally:
        db.close()

@app.task(name='tasks.generate_reorder_list')
def generate_reorder_list():
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine
    from clinic_erp_part4 import InventoryManager
    
    engine = create_engine(os.getenv('DATABASE_URL'))
    Session = sessionmaker(bind=engine)
    db = Session()
    
    try:
        inventory = InventoryManager(db)
        reorder = inventory.generate_reorder_list()
        
        if reorder:
            # Generate and send purchase order
            pass
        
        return f"Generated reorder list with {len(reorder)} items"
    finally:
        db.close()

@app.task(name='tasks.backup_database')
def backup_database():
    import subprocess
    from datetime import datetime
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"/backups/clinic_erp_{timestamp}.sql"
    
    subprocess.run([
        'pg_dump',
        '-h', 'postgres',
        '-U', 'clinic_user',
        '-d', 'clinic_erp',
        '-F', 'c',
        '-f', backup_file
    ])
    
    return f"Database backed up to {backup_file}"
"""

# ==================== USAGE DOCUMENTATION ====================

USAGE_GUIDE = """
# Clinic Management System ERP - Deployment Guide

## 🚀 Quick Start

### 1. Prerequisites
- Docker & Docker Compose installed
- SSL certificates (for production)
- SMTP credentials for email
- SMS provider credentials (optional)

### 2. Initial Setup

```bash
# Clone or create project directory
mkdir clinic-erp && cd clinic-erp

# Create all Python files (Part 1-5)
# Create configuration files (docker-compose.yml, etc.)

# Create .env file with your credentials
cp .env.example .env
nano .env  # Edit with your values

# Start services
docker-compose up -d

# Check services status
docker-compose ps
```

### 3. Initialize Database

```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Create initial admin user
docker-compose exec api python -c "
from clinic_erp_part1 import *
from clinic_erp_part2 import get_db
from sqlalchemy.orm import Session

db = next(get_db())
salt = SecurityManager.generate_salt()
admin = User(
    username='admin',
    email='admin@clinic.com',
    password_hash=SecurityManager.hash_password('Admin@123', salt),
    salt=salt,
    role='admin',
    is_active=True
)
db.add(admin)
db.commit()
print('Admin user created!')
"
```

### 4. Access the System

- **Frontend**: http://localhost:8501
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

**Default Credentials**:
- Username: `admin`
- Password: `Admin@123`

## 📋 User Roles & Permissions

### Admin
- Full system access
- User management
- System configuration
- Analytics and reports

### Doctor
- Patient records (assigned patients)
- Appointments
- Prescriptions
- Teleconsultation
- Medical records

### Nurse
- Patient records (view)
- Appointments (view/update)
- Vitals recording
- Medication administration

### Pharmacist
- Inventory management
- Prescription dispensing
- Stock management
- Expiry tracking

### Receptionist
- Patient registration
- Appointment booking
- Basic patient search

### Manager
- Analytics dashboards
- Financial reports
- Location intelligence
- Staff performance

## 🔒 Security Features

1. **Authentication**
   - JWT tokens with expiration
   - Password hashing (PBKDF2-SHA256)
   - Multi-factor authentication support
   - Account lockout after failed attempts

2. **Authorization**
   - Role-based access control (RBAC)
   - Resource-level permissions
   - Audit logging for all actions

3. **Network Security**
   - HTTPS/TLS encryption
   - Rate limiting
   - CORS protection
   - SQL injection prevention
   - XSS protection

4. **Data Protection**
   - Encrypted sensitive data
   - HIPAA/GDPR compliance
   - Regular backups
   - Data retention policies

## 📊 Performance Optimization

1. **Database**
   - Composite indexes for common queries
   - Query result caching (Redis)
   - Connection pooling
   - Materialized views for analytics

2. **API**
   - Async operations
   - Response compression
   - CDN for static assets
   - Load balancing (Nginx)

3. **Frontend**
   - Lazy loading
   - State management
   - Pagination for large datasets

## 🔧 Maintenance

### Daily Tasks
```bash
# Check service health
docker-compose exec api curl http://localhost:8000/api/health

# View logs
docker-compose logs -f --tail=100

# Monitor resource usage
docker stats
```

### Weekly Tasks
```bash
# Backup database
docker-compose exec postgres pg_dump -U clinic_user clinic_erp > backup.sql

# Check disk space
df -h

# Review audit logs
docker-compose exec api python scripts/analyze_audit_logs.py
```

### Monthly Tasks
- Update dependencies
- Review security logs
- Performance analysis
- User access review

## 🐛 Troubleshooting

### Service won't start
```bash
# Check logs
docker-compose logs api

# Restart services
docker-compose restart

# Rebuild if needed
docker-compose up -d --build
```

### Database connection issues
```bash
# Check database status
docker-compose exec postgres pg_isready

# Reset database (CAUTION: data loss)
docker-compose down -v
docker-compose up -d
```

### Performance issues
```bash
# Check database query performance
docker-compose exec postgres psql -U clinic_user -d clinic_erp -c "
SELECT query, calls, total_time, mean_time 
FROM pg_stat_statements 
ORDER BY total_time DESC 
LIMIT 10;
"
```

## 📈 Monitoring

### Key Metrics to Monitor
- API response time
- Database query performance
- Appointment booking rate
- Prescription dispensing time
- Stock levels
- User activity

### Alerting
Configure alerts for:
- Service downtime
- High error rates
- Low stock levels
- Expiring medicines
- Failed backups

## 🔄 Updates & Maintenance

```bash
# Pull latest changes
git pull origin main

# Update dependencies
docker-compose exec api pip install -r requirements.txt --upgrade

# Run migrations
docker-compose exec api alembic upgrade head

# Restart services
docker-compose restart
```

## 📞 Support

For issues or questions:
- Check documentation: /docs
- View API documentation: http://localhost:8000/docs
- Contact: support@clinic.com

## 🎯 Best Practices

1. **Regular Backups**: Automate daily database backups
2. **Security Updates**: Keep all dependencies updated
3. **Monitoring**: Set up comprehensive monitoring
4. **Testing**: Test all changes in staging environment
5. **Documentation**: Keep documentation updated
6. **Audit**: Regular security audits
7. **Training**: Train staff on system usage
8. **Compliance**: Ensure HIPAA/GDPR compliance

---

## Production Checklist

Before going live:

- [ ] Change all default passwords
- [ ] Generate strong SECRET_KEY
- [ ] Configure SSL certificates
- [ ] Set up backup automation
- [ ] Configure monitoring
- [ ] Set up alerting
- [ ] Review security settings
- [ ] Test disaster recovery
- [ ] Train staff
- [ ] Document procedures
- [ ] Set up logging aggregation
- [ ] Configure rate limiting
- [ ] Test load capacity
- [ ] Review compliance requirements
- [ ] Set up incident response plan
"""

print(USAGE_GUIDE)
print("\n✅ Deployment configuration and documentation complete!")
print("📚 Review the usage guide above for deployment instructions")
print("🔒 Remember to secure all sensitive credentials before production deployment")
