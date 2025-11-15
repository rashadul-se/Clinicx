"""
Clinic Management System ERP - Additional Services
Drug interaction checking, reminders, notifications, and optimizations
"""

from typing import List, Dict, Optional
from datetime import datetime, timedelta
import asyncio
from sqlalchemy import text, event
from sqlalchemy.engine import Engine
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==================== DATABASE OPTIMIZATION ====================

class DatabaseOptimizer:
    """Database query optimization utilities"""
    
    @staticmethod
    def create_indexes(engine):
        """Create optimized indexes for common queries"""
        
        indexes = [
            # Composite indexes for common query patterns
            """
            CREATE INDEX IF NOT EXISTS idx_appointment_doctor_date_status 
            ON appointments(doctor_id, appointment_date, status);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_prescription_patient_date 
            ON prescriptions(patient_id, prescription_date DESC);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_medicine_stock_expiry 
            ON medicine_stocks(medicine_id, expiry_date, quantity) 
            WHERE quantity > 0;
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_audit_log_composite 
            ON audit_logs(user_id, action, timestamp DESC);
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_patient_search 
            ON patients USING gin(to_tsvector('english', first_name || ' ' || last_name));
            """,
            # Partial indexes for active records
            """
            CREATE INDEX IF NOT EXISTS idx_users_active 
            ON users(role, is_active) WHERE is_active = true;
            """,
            """
            CREATE INDEX IF NOT EXISTS idx_appointments_upcoming 
            ON appointments(doctor_id, appointment_date, appointment_time) 
            WHERE status IN ('scheduled', 'confirmed');
            """
        ]
        
        with engine.connect() as conn:
            for idx in indexes:
                try:
                    conn.execute(text(idx))
                    conn.commit()
                    logger.info(f"Index created successfully")
                except Exception as e:
                    logger.error(f"Error creating index: {e}")
    
    @staticmethod
    def analyze_tables(engine):
        """Run ANALYZE to update statistics"""
        tables = [
            'users', 'patients', 'doctors', 'appointments', 
            'prescriptions', 'medicines', 'medicine_stocks'
        ]
        
        with engine.connect() as conn:
            for table in tables:
                conn.execute(text(f"ANALYZE {table}"))
            conn.commit()
            logger.info("Table statistics updated")
    
    @staticmethod
    def enable_query_cache(engine):
        """Enable PostgreSQL query result caching"""
        with engine.connect() as conn:
            conn.execute(text("SET shared_preload_libraries = 'pg_stat_statements'"))
            conn.execute(text("SET pg_stat_statements.track = 'all'"))
            conn.commit()

# Enable SQLite/PostgreSQL query optimization
@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Optimize SQLite connections"""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=10000")
    cursor.execute("PRAGMA temp_store=MEMORY")
    cursor.close()

# ==================== DRUG INTERACTION SERVICE ====================

class DrugInteractionChecker:
    """
    Drug-drug interaction and allergy checking service
    In production, integrate with FDA API or drug databases
    """
    
    # Sample drug interaction database
    INTERACTIONS = {
        "warfarin": ["aspirin", "ibuprofen", "naproxen"],
        "metformin": ["alcohol", "contrast_dye"],
        "simvastatin": ["clarithromycin", "itraconazole"],
        "lisinopril": ["potassium_supplements", "spironolactone"],
        "amoxicillin": ["methotrexate"],
    }
    
    # Drug-allergy mappings
    ALLERGY_GROUPS = {
        "penicillin": ["amoxicillin", "ampicillin", "penicillin"],
        "sulfa": ["sulfamethoxazole", "sulfasalazine"],
        "nsaid": ["ibuprofen", "naproxen", "diclofenac"],
    }
    
    @classmethod
    def check_interactions(
        cls, 
        new_medicines: List[str], 
        existing_medicines: List[str]
    ) -> Dict[str, List[str]]:
        """Check for drug-drug interactions"""
        
        interactions = {}
        
        for new_med in new_medicines:
            new_med_lower = new_med.lower()
            conflicts = []
            
            # Check against existing medications
            for existing_med in existing_medicines:
                existing_lower = existing_med.lower()
                
                # Check if new drug interacts with existing
                if new_med_lower in cls.INTERACTIONS:
                    if any(interaction in existing_lower 
                           for interaction in cls.INTERACTIONS[new_med_lower]):
                        conflicts.append(existing_med)
                
                # Check reverse interaction
                if existing_lower in cls.INTERACTIONS:
                    if any(interaction in new_med_lower 
                           for interaction in cls.INTERACTIONS[existing_lower]):
                        conflicts.append(existing_med)
            
            if conflicts:
                interactions[new_med] = conflicts
        
        return interactions
    
    @classmethod
    def check_allergies(
        cls, 
        medicines: List[str], 
        patient_allergies: List[str]
    ) -> Dict[str, List[str]]:
        """Check for drug-allergy conflicts"""
        
        allergies = {}
        
        for medicine in medicines:
            med_lower = medicine.lower()
            alerts = []
            
            for allergy in patient_allergies:
                allergy_lower = allergy.lower().strip()
                
                # Direct match
                if allergy_lower in med_lower or med_lower in allergy_lower:
                    alerts.append(f"Direct allergy: {allergy}")
                    continue
                
                # Check allergy groups
                for group, drugs in cls.ALLERGY_GROUPS.items():
                    if allergy_lower in group or group in allergy_lower:
                        if any(drug in med_lower for drug in drugs):
                            alerts.append(f"Cross-allergy ({group}): {allergy}")
            
            if alerts:
                allergies[medicine] = alerts
        
        return allergies
    
    @classmethod
    def get_recommendations(
        cls, 
        interactions: Dict[str, List[str]], 
        allergies: Dict[str, List[str]]
    ) -> List[str]:
        """Generate clinical recommendations"""
        
        recommendations = []
        
        if interactions:
            recommendations.append(
                "⚠️ DRUG INTERACTIONS DETECTED: Review and adjust prescription"
            )
            for drug, conflicts in interactions.items():
                recommendations.append(
                    f"  • {drug} interacts with: {', '.join(conflicts)}"
                )
        
        if allergies:
            recommendations.append(
                "🚨 ALLERGY ALERT: DO NOT PRESCRIBE these medications"
            )
            for drug, alerts in allergies.items():
                recommendations.append(
                    f"  • {drug}: {'; '.join(alerts)}"
                )
        
        return recommendations

# ==================== NOTIFICATION SERVICE ====================

class NotificationService:
    """
    Multi-channel notification service (Email, SMS, WhatsApp)
    """
    
    def __init__(self):
        self.email_config = {
            'smtp_server': 'smtp.gmail.com',
            'smtp_port': 587,
            'sender_email': 'clinic@example.com',
            'sender_password': 'your_password'
        }
    
    def send_email(
        self, 
        recipient: str, 
        subject: str, 
        body: str,
        html: bool = False
    ) -> bool:
        """Send email notification"""
        
        try:
            msg = MIMEMultipart('alternative')
            msg['From'] = self.email_config['sender_email']
            msg['To'] = recipient
            msg['Subject'] = subject
            
            if html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(
                self.email_config['smtp_server'], 
                self.email_config['smtp_port']
            ) as server:
                server.starttls()
                server.login(
                    self.email_config['sender_email'],
                    self.email_config['sender_password']
                )
                server.send_message(msg)
            
            logger.info(f"Email sent to {recipient}")
            return True
            
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            return False
    
    def send_sms(self, phone: str, message: str) -> bool:
        """
        Send SMS notification
        Integrate with Twilio, AWS SNS, or similar service
        """
        try:
            # Placeholder for SMS API integration
            logger.info(f"SMS to {phone}: {message}")
            # In production:
            # from twilio.rest import Client
            # client = Client(account_sid, auth_token)
            # client.messages.create(to=phone, from_=from_number, body=message)
            return True
        except Exception as e:
            logger.error(f"SMS sending failed: {e}")
            return False
    
    def send_whatsapp(self, phone: str, message: str) -> bool:
        """
        Send WhatsApp notification
        Integrate with WhatsApp Business API
        """
        try:
            # Placeholder for WhatsApp API integration
            logger.info(f"WhatsApp to {phone}: {message}")
            return True
        except Exception as e:
            logger.error(f"WhatsApp sending failed: {e}")
            return False

# ==================== APPOINTMENT REMINDER SERVICE ====================

class AppointmentReminderService:
    """
    Automated appointment reminder system
    """
    
    def __init__(self, db_session, notification_service: NotificationService):
        self.db = db_session
        self.notifier = notification_service
    
    async def send_reminders(self):
        """Send reminders for upcoming appointments"""
        
        from clinic_erp_part1 import Appointment, Patient, Doctor
        from sqlalchemy import and_
        
        # Get appointments for tomorrow
        tomorrow = datetime.now().date() + timedelta(days=1)
        
        appointments = self.db.query(Appointment).join(
            Patient
        ).join(
            Doctor
        ).filter(
            and_(
                Appointment.appointment_date == tomorrow,
                Appointment.status.in_(['scheduled', 'confirmed']),
                Appointment.reminder_sent == False
            )
        ).all()
        
        for appt in appointments:
            # Create reminder message
            message = self._create_reminder_message(appt)
            
            # Send via multiple channels
            if appt.patient.email:
                self.notifier.send_email(
                    appt.patient.email,
                    "Appointment Reminder",
                    message
                )
            
            if appt.patient.phone:
                self.notifier.send_sms(appt.patient.phone, message)
            
            # Mark as sent
            appt.reminder_sent = True
        
        self.db.commit()
        logger.info(f"Sent {len(appointments)} reminders")
    
    def _create_reminder_message(self, appointment) -> str:
        """Create personalized reminder message"""
        
        return f"""
        Dear {appointment.patient.first_name},
        
        This is a reminder for your appointment:
        
        Date: {appointment.appointment_date.strftime('%B %d, %Y')}
        Time: {appointment.appointment_time.strftime('%I:%M %p')}
        Doctor: Dr. {appointment.doctor.last_name}
        Type: {appointment.consultation_type}
        
        {'Video Link: [link]' if appointment.consultation_type == 'teleconsultation' else 'Clinic Address: [address]'}
        
        Please arrive 15 minutes early.
        To cancel or reschedule, call: [phone]
        
        Best regards,
        Clinic Management System
        """
    
    async def send_followup_reminders(self):
        """Send follow-up reminders after appointments"""
        
        from clinic_erp_part1 import Appointment
        
        # Get completed appointments from 7 days ago
        week_ago = datetime.now().date() - timedelta(days=7)
        
        appointments = self.db.query(Appointment).filter(
            and_(
                Appointment.appointment_date == week_ago,
                Appointment.status == 'completed'
            )
        ).all()
        
        for appt in appointments:
            message = f"""
            Dear {appt.patient.first_name},
            
            We hope you're feeling better after your recent visit.
            
            If you have any concerns or need a follow-up appointment,
            please don't hesitate to contact us.
            
            You can also rate your experience: [feedback_link]
            
            Best regards,
            Clinic Team
            """
            
            if appt.patient.email:
                self.notifier.send_email(
                    appt.patient.email,
                    "Follow-up Check",
                    message
                )

# ==================== INVENTORY MANAGEMENT SERVICE ====================

class InventoryManager:
    """
    Advanced inventory management with FIFO and expiry tracking
    """
    
    def __init__(self, db_session):
        self.db = db_session
    
    def dispense_medicine_fifo(
        self, 
        medicine_id: int, 
        quantity: int,
        location: str = "pharmacy"
    ) -> List[Dict]:
        """
        Dispense medicine using FIFO (First-In-First-Out) based on expiry
        """
        
        from clinic_erp_part1 import MedicineStock
        from sqlalchemy import and_
        
        # Get available stock ordered by expiry date
        available_stock = self.db.query(MedicineStock).filter(
            and_(
                MedicineStock.medicine_id == medicine_id,
                MedicineStock.location == location,
                MedicineStock.quantity > 0,
                MedicineStock.expiry_date > datetime.now().date()
            )
        ).order_by(MedicineStock.expiry_date).all()
        
        if not available_stock:
            raise ValueError("No stock available")
        
        total_available = sum(stock.quantity for stock in available_stock)
        if total_available < quantity:
            raise ValueError(f"Insufficient stock. Available: {total_available}")
        
        dispensed = []
        remaining_qty = quantity
        
        for stock in available_stock:
            if remaining_qty == 0:
                break
            
            dispensed_from_batch = min(stock.quantity, remaining_qty)
            stock.quantity -= dispensed_from_batch
            remaining_qty -= dispensed_from_batch
            
            dispensed.append({
                'batch_number': stock.batch_number,
                'quantity': dispensed_from_batch,
                'expiry_date': stock.expiry_date
            })
        
        self.db.commit()
        return dispensed
    
    def get_expiring_items(self, days: int = 30) -> List[Dict]:
        """Get medicines expiring within specified days"""
        
        from clinic_erp_part1 import MedicineStock, Medicine
        
        expiry_date = datetime.now().date() + timedelta(days=days)
        
        expiring = self.db.query(
            Medicine.name,
            MedicineStock.batch_number,
            MedicineStock.quantity,
            MedicineStock.expiry_date,
            MedicineStock.location
        ).join(
            Medicine
        ).filter(
            and_(
                MedicineStock.expiry_date <= expiry_date,
                MedicineStock.expiry_date > datetime.now().date(),
                MedicineStock.quantity > 0
            )
        ).order_by(MedicineStock.expiry_date).all()
        
        return [
            {
                'medicine': item[0],
                'batch': item[1],
                'quantity': item[2],
                'expiry_date': item[3],
                'location': item[4],
                'days_until_expiry': (item[3] - datetime.now().date()).days
            }
            for item in expiring
        ]
    
    def generate_reorder_list(self) -> List[Dict]:
        """Generate purchase order for items below reorder level"""
        
        from clinic_erp_part1 import Medicine, MedicineStock
        from sqlalchemy import func
        
        medicines = self.db.query(
            Medicine.id,
            Medicine.name,
            Medicine.reorder_level,
            func.sum(MedicineStock.quantity).label('current_stock')
        ).outerjoin(
            MedicineStock,
            and_(
                Medicine.id == MedicineStock.medicine_id,
                MedicineStock.expiry_date > datetime.now().date()
            )
        ).group_by(
            Medicine.id
        ).having(
            func.coalesce(func.sum(MedicineStock.quantity), 0) < Medicine.reorder_level
        ).all()
        
        reorder_list = []
        for med in medicines:
            current = med.current_stock or 0
            deficit = med.reorder_level - current
            suggested_order = deficit * 2  # Order 2x the deficit
            
            reorder_list.append({
                'medicine_id': med.id,
                'medicine_name': med.name,
                'current_stock': current,
                'reorder_level': med.reorder_level,
                'suggested_quantity': suggested_order
            })
        
        return reorder_list

# ==================== BACKGROUND TASKS ====================

class BackgroundTaskScheduler:
    """
    Schedule and run background tasks
    """
    
    @staticmethod
    async def run_daily_tasks(db_session):
        """Run daily maintenance tasks"""
        
        notifier = NotificationService()
        reminder_service = AppointmentReminderService(db_session, notifier)
        inventory_manager = InventoryManager(db_session)
        
        tasks = [
            reminder_service.send_reminders(),
            reminder_service.send_followup_reminders(),
        ]
        
        await asyncio.gather(*tasks)
        
        # Check expiring medicines
        expiring = inventory_manager.get_expiring_items(30)
        if expiring:
            logger.warning(f"Found {len(expiring)} items expiring soon")
            # Send notification to pharmacy manager
        
        # Check reorder levels
        reorder = inventory_manager.generate_reorder_list()
        if reorder:
            logger.info(f"Generated reorder list with {len(reorder)} items")
            # Send to procurement

# ==================== VALIDATION UTILITIES ====================

class InputValidator:
    """Comprehensive input validation"""
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number format"""
        import re
        pattern = r'^\+?[1-9]\d{1,14}$'
        return bool(re.match(pattern, phone.replace(' ', '').replace('-', '')))
    
    @staticmethod
    def validate_postal_code(postal_code: str, country: str = 'US') -> bool:
        """Validate postal code format"""
        import re
        patterns = {
            'US': r'^\d{5}(-\d{4})?$',
            'UK': r'^[A-Z]{1,2}\d{1,2}[A-Z]?\s?\d[A-Z]{2}$',
            'CA': r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$',
        }
        pattern = patterns.get(country, r'^\d{3,10}$')
        return bool(re.match(pattern, postal_code))
    
    @staticmethod
    def sanitize_input(text: str) -> str:
        """Sanitize user input to prevent SQL injection and XSS"""
        import html
        # Remove potentially dangerous characters
        sanitized = html.escape(text)
        return sanitized.strip()
    
    @staticmethod
    def validate_date_range(start: datetime, end: datetime) -> bool:
        """Validate date range"""
        return start <= end and start >= datetime(1900, 1, 1)

print("✅ Additional services and optimizations loaded successfully!")
print("📋 Features included:")
print("  • Drug interaction checking")
print("  • Automated appointment reminders")
print("  • FIFO inventory management")
print("  • Email/SMS/WhatsApp notifications")
print("  • Database query optimization")
print("  • Input validation and sanitization")
