"""
Clinic Management System ERP - Streamlit Frontend
Interactive dashboard with role-based views
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
from typing import Optional, Dict, List
import json

# ==================== CONFIGURATION ====================

API_BASE_URL = "http://localhost:8000/api"

# Page configuration
st.set_page_config(
    page_title="Clinic Management System",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== SESSION STATE MANAGEMENT ====================

if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'user' not in st.session_state:
    st.session_state.user = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "dashboard"

# ==================== API CLIENT ====================

class APIClient:
    """API client with authentication"""
    
    @staticmethod
    def get_headers():
        if st.session_state.access_token:
            return {
                "Authorization": f"Bearer {st.session_state.access_token}",
                "Content-Type": "application/json"
            }
        return {"Content-Type": "application/json"}
    
    @staticmethod
    def login(username: str, password: str) -> Dict:
        response = requests.post(
            f"{API_BASE_URL}/auth/login",
            json={"username": username, "password": password}
        )
        return response.json() if response.status_code == 200 else None
    
    @staticmethod
    def get(endpoint: str, params: Optional[Dict] = None):
        try:
            response = requests.get(
                f"{API_BASE_URL}/{endpoint}",
                headers=APIClient.get_headers(),
                params=params
            )
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            st.error(f"API Error: {str(e)}")
            return None
    
    @staticmethod
    def post(endpoint: str, data: Dict):
        try:
            response = requests.post(
                f"{API_BASE_URL}/{endpoint}",
                headers=APIClient.get_headers(),
                json=data
            )
            if response.status_code in [200, 201]:
                return response.json()
            else:
                st.error(f"Error: {response.json().get('detail', 'Unknown error')}")
                return None
        except Exception as e:
            st.error(f"API Error: {str(e)}")
            return None

# ==================== AUTHENTICATION ====================

def login_page():
    """Login interface"""
    st.title("🏥 Clinic Management System")
    st.subheader("Login")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if username and password:
                    result = APIClient.login(username, password)
                    
                    if result and 'access_token' in result:
                        st.session_state.access_token = result['access_token']
                        st.session_state.user = result['user']
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                else:
                    st.warning("Please enter username and password")

def logout():
    """Logout function"""
    st.session_state.access_token = None
    st.session_state.user = None
    st.rerun()

# ==================== SIDEBAR NAVIGATION ====================

def render_sidebar():
    """Render sidebar navigation based on user role"""
    with st.sidebar:
        st.title("🏥 CMS ERP")
        st.write(f"Welcome, **{st.session_state.user['username']}**")
        st.write(f"Role: *{st.session_state.user['role'].title()}*")
        st.divider()
        
        role = st.session_state.user['role']
        
        # Common pages
        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state.current_page = "dashboard"
            st.rerun()
        
        # Role-specific pages
        if role in ['admin', 'doctor', 'nurse', 'receptionist']:
            if st.button("👥 Patients", use_container_width=True):
                st.session_state.current_page = "patients"
                st.rerun()
        
        if role in ['admin', 'doctor', 'nurse', 'receptionist']:
            if st.button("📅 Appointments", use_container_width=True):
                st.session_state.current_page = "appointments"
                st.rerun()
        
        if role in ['admin', 'doctor']:
            if st.button("💊 Prescriptions", use_container_width=True):
                st.session_state.current_page = "prescriptions"
                st.rerun()
        
        if role in ['admin', 'pharmacist']:
            if st.button("📦 Inventory", use_container_width=True):
                st.session_state.current_page = "inventory"
                st.rerun()
        
        if role in ['admin', 'manager']:
            if st.button("📈 Analytics", use_container_width=True):
                st.session_state.current_page = "analytics"
                st.rerun()
        
        if role == 'doctor':
            if st.button("🎥 Teleconsultations", use_container_width=True):
                st.session_state.current_page = "teleconsult"
                st.rerun()
        
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            logout()

# ==================== DASHBOARD PAGE ====================

def dashboard_page():
    """Main dashboard with KPIs"""
    st.title("📊 Dashboard")
    
    # KPI Cards
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Today's Appointments",
            value="24",
            delta="3"
        )
    
    with col2:
        st.metric(
            label="Pending Prescriptions",
            value="12",
            delta="-2"
        )
    
    with col3:
        st.metric(
            label="Active Patients",
            value="1,234",
            delta="45"
        )
    
    with col4:
        st.metric(
            label="Low Stock Items",
            value="8",
            delta="-3"
        )
    
    st.divider()
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Appointments This Week")
        # Sample data
        df_appointments = pd.DataFrame({
            'Day': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'In-Person': [15, 18, 20, 17, 22, 10, 5],
            'Teleconsult': [5, 7, 8, 6, 9, 4, 2]
        })
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=df_appointments['Day'], y=df_appointments['In-Person'], name='In-Person'))
        fig.add_trace(go.Bar(x=df_appointments['Day'], y=df_appointments['Teleconsult'], name='Teleconsult'))
        fig.update_layout(barmode='stack', height=300)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Patient Distribution by Postal Code")
        # Sample data
        df_postal = pd.DataFrame({
            'Postal Code': ['10001', '10002', '10003', '10004', '10005'],
            'Patients': [234, 189, 156, 142, 98]
        })
        
        fig = px.pie(df_postal, values='Patients', names='Postal Code', height=300)
        st.plotly_chart(fig, use_container_width=True)

# ==================== PATIENTS PAGE ====================

def patients_page():
    """Patient management interface"""
    st.title("👥 Patient Management")
    
    tab1, tab2 = st.tabs(["Search Patients", "Register New Patient"])
    
    with tab1:
        st.subheader("Search Patients")
        
        col1, col2, col3 = st.columns([3, 2, 1])
        with col1:
            search_query = st.text_input("Search by Name, PID, or Phone")
        with col2:
            postal_filter = st.text_input("Postal Code Filter")
        with col3:
            search_btn = st.button("Search", use_container_width=True)
        
        if search_query or search_btn:
            # Mock data - replace with API call
            patients_data = [
                {"pid": "PID20241115000001", "name": "John Doe", "age": 45, "phone": "+1234567890", "postal": "10001"},
                {"pid": "PID20241115000002", "name": "Jane Smith", "age": 32, "phone": "+1234567891", "postal": "10002"},
            ]
            
            df = pd.DataFrame(patients_data)
            st.dataframe(df, use_container_width=True)
            
            # Patient details
            selected_pid = st.selectbox("Select Patient for Details", df['pid'].tolist())
            if selected_pid:
                st.subheader("Patient Details")
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**PID:**", selected_pid)
                    st.write("**Name:** John Doe")
                    st.write("**Age:** 45 years")
                    st.write("**Blood Group:** O+")
                with col2:
                    st.write("**Phone:** +1234567890")
                    st.write("**Email:** john.doe@email.com")
                    st.write("**Address:** 123 Main St, 10001")
                    st.write("**Allergies:** Penicillin")
    
    with tab2:
        st.subheader("Register New Patient")
        
        with st.form("patient_registration"):
            col1, col2 = st.columns(2)
            
            with col1:
                first_name = st.text_input("First Name*")
                last_name = st.text_input("Last Name*")
                dob = st.date_input("Date of Birth*", max_value=date.today())
                gender = st.selectbox("Gender*", ["Male", "Female", "Other"])
                phone = st.text_input("Phone*")
            
            with col2:
                email = st.text_input("Email")
                postal_code = st.text_input("Postal Code*")
                address = st.text_area("Address*")
                blood_group = st.selectbox("Blood Group", ["", "A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"])
                allergies = st.text_input("Allergies (comma-separated)")
            
            col3, col4 = st.columns(2)
            with col3:
                insurance_provider = st.text_input("Insurance Provider")
            with col4:
                insurance_number = st.text_input("Insurance Number")
            
            submit = st.form_submit_button("Register Patient", use_container_width=True)
            
            if submit:
                if first_name and last_name and phone and postal_code and address:
                    patient_data = {
                        "first_name": first_name,
                        "last_name": last_name,
                        "date_of_birth": str(dob),
                        "gender": gender,
                        "phone": phone,
                        "email": email,
                        "postal_code": postal_code,
                        "address": address,
                        "blood_group": blood_group,
                        "allergies": allergies,
                        "insurance_provider": insurance_provider,
                        "insurance_number": insurance_number
                    }
                    
                    result = APIClient.post("patients", patient_data)
                    if result:
                        st.success(f"Patient registered successfully! PID: {result.get('pid', 'N/A')}")
                else:
                    st.error("Please fill all required fields")

# ==================== APPOINTMENTS PAGE ====================

def appointments_page():
    """Appointment scheduling interface"""
    st.title("📅 Appointment Management")
    
    tab1, tab2 = st.tabs(["View Appointments", "Book New Appointment"])
    
    with tab1:
        st.subheader("Appointments Calendar")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            view_date = st.date_input("Select Date", value=date.today())
        with col2:
            doctor_filter = st.selectbox("Filter by Doctor", ["All Doctors", "Dr. Smith", "Dr. Johnson"])
        with col3:
            status_filter = st.selectbox("Status", ["All", "Scheduled", "Completed", "Cancelled"])
        
        # Mock appointment data
        appointments = [
            {"time": "09:00", "patient": "John Doe", "doctor": "Dr. Smith", "type": "In-Person", "status": "Scheduled"},
            {"time": "10:00", "patient": "Jane Smith", "doctor": "Dr. Smith", "type": "Teleconsult", "status": "Scheduled"},
            {"time": "11:00", "patient": "Bob Wilson", "doctor": "Dr. Johnson", "type": "In-Person", "status": "Completed"},
        ]
        
        df = pd.DataFrame(appointments)
        st.dataframe(df, use_container_width=True)
        
        # Quick actions
        st.subheader("Quick Actions")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("Mark as Completed", use_container_width=True):
                st.success("Appointment marked as completed")
        with col2:
            if st.button("Cancel Appointment", use_container_width=True):
                st.warning("Appointment cancelled")
        with col3:
            if st.button("Send Reminder", use_container_width=True):
                st.info("Reminder sent to patient")
    
    with tab2:
        st.subheader("Book New Appointment")
        
        with st.form("appointment_booking"):
            col1, col2 = st.columns(2)
            
            with col1:
                patient_search = st.text_input("Search Patient (PID or Name)")
                doctor_select = st.selectbox("Select Doctor", ["Dr. Smith (Cardiology)", "Dr. Johnson (General Medicine)"])
                appointment_date = st.date_input("Appointment Date", min_value=date.today())
            
            with col2:
                consultation_type = st.radio("Consultation Type", ["In-Person", "Teleconsultation"])
                appointment_time = st.time_input("Appointment Time")
                chief_complaint = st.text_area("Chief Complaint")
            
            submit = st.form_submit_button("Book Appointment", use_container_width=True)
            
            if submit:
                st.success("Appointment booked successfully!")

# ==================== PRESCRIPTIONS PAGE ====================

def prescriptions_page():
    """E-prescription management"""
    st.title("💊 Prescription Management")
    
    tab1, tab2 = st.tabs(["View Prescriptions", "Create New Prescription"])
    
    with tab1:
        st.subheader("Recent Prescriptions")
        
        prescriptions = [
            {"id": "RX001", "patient": "John Doe", "date": "2024-11-15", "status": "Pending"},
            {"id": "RX002", "patient": "Jane Smith", "date": "2024-11-14", "status": "Dispensed"},
        ]
        
        df = pd.DataFrame(prescriptions)
        st.dataframe(df, use_container_width=True)
    
    with tab2:
        st.subheader("Create New Prescription")
        
        with st.form("prescription_form"):
            patient_search = st.text_input("Search Patient")
            diagnosis = st.text_area("Diagnosis")
            
            st.write("**Medicines**")
            num_medicines = st.number_input("Number of Medicines", min_value=1, max_value=10, value=1)
            
            medicines = []
            for i in range(num_medicines):
                st.write(f"Medicine {i+1}")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    medicine = st.text_input(f"Medicine Name {i+1}", key=f"med_{i}")
                with col2:
                    dosage = st.text_input(f"Dosage {i+1}", key=f"dose_{i}")
                with col3:
                    frequency = st.selectbox(f"Frequency {i+1}", ["Once daily", "Twice daily", "Thrice daily"], key=f"freq_{i}")
                with col4:
                    duration = st.text_input(f"Duration {i+1}", key=f"dur_{i}")
            
            notes = st.text_area("Additional Notes")
            submit = st.form_submit_button("Create Prescription", use_container_width=True)
            
            if submit:
                st.success("Prescription created successfully!")

# ==================== INVENTORY PAGE ====================

def inventory_page():
    """Inventory management"""
    st.title("📦 Inventory Management")
    
    tab1, tab2, tab3 = st.tabs(["Current Stock", "Expiring Soon", "Reorder Alerts"])
    
    with tab1:
        st.subheader("Current Stock Levels")
        
        search = st.text_input("Search Medicine")
        
        stock_data = [
            {"name": "Paracetamol 500mg", "category": "Analgesic", "stock": 500, "reorder": 100, "expiry": "2025-06-30"},
            {"name": "Amoxicillin 250mg", "category": "Antibiotic", "stock": 45, "reorder": 50, "expiry": "2025-03-15"},
            {"name": "Metformin 500mg", "category": "Antidiabetic", "stock": 200, "reorder": 100, "expiry": "2025-12-31"},
        ]
        
        df = pd.DataFrame(stock_data)
        
        # Color code based on stock levels
        def highlight_low_stock(row):
            if row['stock'] < row['reorder']:
                return ['background-color: #ffcccc'] * len(row)
            return [''] * len(row)
        
        st.dataframe(df.style.apply(highlight_low_stock, axis=1), use_container_width=True)
    
    with tab2:
        st.subheader("Medicines Expiring Soon")
        
        days = st.slider("Show items expiring within (days)", 30, 180, 60)
        
        expiring = [
            {"name": "Amoxicillin 250mg", "batch": "BATCH001", "quantity": 45, "expiry": "2025-03-15", "location": "Pharmacy"},
            {"name": "Ibuprofen 400mg", "batch": "BATCH002", "quantity": 30, "expiry": "2025-04-20", "location": "Ward A"},
        ]
        
        df = pd.DataFrame(expiring)
        st.dataframe(df, use_container_width=True)
        
        if st.button("Generate Expiry Report"):
            st.success("Report generated and sent to pharmacy")
    
    with tab3:
        st.subheader("Reorder Alerts")
        
        reorder_items = [
            {"name": "Amoxicillin 250mg", "current": 45, "reorder_level": 50, "suggested": 200},
            {"name": "Aspirin 75mg", "current": 35, "reorder_level": 40, "suggested": 150},
        ]
        
        df = pd.DataFrame(reorder_items)
        st.dataframe(df, use_container_width=True)
        
        if st.button("Generate Purchase Order"):
            st.success("Purchase order generated for review")

# ==================== ANALYTICS PAGE ====================

def analytics_page():
    """Analytics and reporting"""
    st.title("📈 Analytics & Reports")
    
    tab1, tab2, tab3 = st.tabs(["Patient Demographics", "Financial Overview", "Location Intelligence"])
    
    with tab1:
        st.subheader("Patient Demographics")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Age distribution
            age_data = pd.DataFrame({
                'Age Group': ['0-18', '19-35', '36-50', '51-65', '65+'],
                'Count': [145, 423, 378, 234, 54]
            })
            fig = px.bar(age_data, x='Age Group', y='Count', title="Patients by Age Group")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Gender distribution
            gender_data = pd.DataFrame({
                'Gender': ['Male', 'Female', 'Other'],
                'Count': [612, 598, 24]
            })
            fig = px.pie(gender_data, values='Count', names='Gender', title="Gender Distribution")
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Financial Overview")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Monthly Revenue", "$45,230", "+12%")
        with col2:
            st.metric("Outstanding Bills", "$8,450", "-5%")
        with col3:
            st.metric("Insurance Claims", "$12,340", "+8%")
        
        # Revenue trend
        revenue_data = pd.DataFrame({
            'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
            'Revenue': [35000, 38000, 42000, 39000, 43000, 45000]
        })
        fig = px.line(revenue_data, x='Month', y='Revenue', title="Revenue Trend")
        st.plotly_chart(fig, use_container_width=True)
    
    with tab3:
        st.subheader("Location Intelligence")
        
        # Postal code clustering
        postal_data = pd.DataFrame({
            'Postal Code': ['10001', '10002', '10003', '10004', '10005'],
            'Patients': [234, 189, 156, 142, 98],
            'Avg Consultation Fee': [150, 145, 160, 155, 140]
        })
        
        st.dataframe(postal_data, use_container_width=True)
        
        fig = px.scatter(postal_data, x='Patients', y='Avg Consultation Fee', 
                        size='Patients', text='Postal Code', 
                        title="Patient Volume vs Consultation Fee by Postal Code")
        st.plotly_chart(fig, use_container_width=True)

# ==================== TELECONSULTATION PAGE ====================

def teleconsult_page():
    """Teleconsultation interface"""
    st.title("🎥 Teleconsultation")
    
    st.info("Teleconsultation feature - Video conferencing integration would go here")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Upcoming Teleconsultations")
        
        teleconsults = [
            {"time": "10:00 AM", "patient": "Jane Smith", "room_id": "ROOM_ABC123"},
            {"time": "02:00 PM", "patient": "Bob Wilson", "room_id": "ROOM_XYZ789"},
        ]
        
        for tc in teleconsults:
            with st.container():
                col_a, col_b, col_c = st.columns([2, 2, 1])
                with col_a:
                    st.write(f"**{tc['time']}**")
                with col_b:
                    st.write(tc['patient'])
                with col_c:
                    if st.button("Join", key=tc['room_id']):
                        st.success(f"Joining room {tc['room_id']}")
                st.divider()
    
    with col2:
        st.subheader("Quick Actions")
        if st.button("Start Instant Consultation", use_container_width=True):
            st.info("Instant consultation room created")
        if st.button("View Recording History", use_container_width=True):
            st.info("Loading recordings...")

# ==================== MAIN APP ====================

def main():
    """Main application logic"""
    if not st.session_state.access_token:
        login_page()
    else:
        render_sidebar()
        
        # Route to appropriate page
        if st.session_state.current_page == "dashboard":
            dashboard_page()
        elif st.session_state.current_page == "patients":
            patients_page()
        elif st.session_state.current_page == "appointments":
            appointments_page()
        elif st.session_state.current_page == "prescriptions":
            prescriptions_page()
        elif st.session_state.current_page == "inventory":
            inventory_page()
        elif st.session_state.current_page == "analytics":
            analytics_page()
        elif st.session_state.current_page == "teleconsult":
            teleconsult_page()

if __name__ == "__main__":
    main()

print("✅ Streamlit frontend initialized!")
print("🚀 Run with: streamlit run clinic_erp_part3.py")
