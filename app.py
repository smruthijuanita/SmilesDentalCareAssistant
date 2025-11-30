import streamlit as st
from hashlib import sha256
from datetime import datetime, date
import pandas as pd
from email.message import EmailMessage
import smtplib
import logging

# local modules
from modules.settings import get_settings
from modules.db import (
    init_db,
    create_user,
    authenticate,
    save_booking,
    list_bookings,
    update_booking_status,
    save_upload as db_save_upload,
)
from modules.file_utils import save_uploaded_file, extract_pdf_text
from modules.ui_components import inject_css, app_header
from modules.admin_utils import calculate_admin_metrics, get_frequent_patients, get_bookings_per_day

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Optional modules
try:
    from modules.rag_pipeline import RAGPipeline
except Exception:
    RAGPipeline = None

try:
    from modules.chat_engine import ChatEngine
except Exception:
    ChatEngine = None


# ---------------------------------------------
# App config + styles
# ---------------------------------------------
st.set_page_config(page_title="Smiles Dental Care", page_icon="🩺", layout="wide")
inject_css()
app_header()
init_db()
settings = get_settings()


# ---------------------------------------------
# Session state initialization
# ---------------------------------------------
def init_session_state():
    if "user" not in st.session_state:
        st.session_state.user = None
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "booking_flow" not in st.session_state:
        st.session_state.booking_flow = {
            "active": False,
            "slots": {
                "name": None,
                "email": None,
                "phone": None,
                "booking_type": None,
                "date": None,
                "time": None,
            },
            "awaiting_field": None,
            "booking_id": None,
        }
    if "rag_index" not in st.session_state:
        st.session_state.rag_index = None

init_session_state()


# ---------------------------------------------
# Compatibility: safe rerun wrapper
# ---------------------------------------------
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    elif hasattr(st, "experimental_rerun"):
        st.experimental_rerun()
    else:
        st.stop()


# ---------------------------------------------
# Helpers
# ---------------------------------------------
def hash_password(password: str) -> str:
    return sha256(password.encode()).hexdigest()

def has_id_proof(user_id: str) -> bool:
    # This would ideally check the DB. For now, we can check if they have uploaded anything.
    # Since we don't have a direct 'check_upload' in db.py, we might need to rely on list_uploads or similar.
    # For this refactor, we will assume False if we can't check easily, or implement a check.
    # Let's use a simple check if possible, or skip to avoid breaking if db doesn't support it yet.
    # The original code used a direct SQL query. We should add a method to db.py or supabase_client.
    # For now, we'll return False to prompt upload, or we can try to query uploads table if we added a method.
    # We will skip this check for now to keep it simple, or assume False.
    return False

def has_booking_conflict(appt_date: date, appt_time: str) -> bool:
    # Fetch all bookings and check. In a real app, do this server-side with a count query.
    # Since we are using Supabase, we should ideally add a method `check_availability`.
    # For now, we will fetch recent bookings and check in memory (not efficient but works for small scale).
    bookings = list_bookings()
    d_str = appt_date.isoformat()
    for b in bookings:
        if b.get('appt_date') == d_str and b.get('appt_time') == appt_time and b.get('status') != 'Cancelled':
            return True
    return False


# ---------------------------------------------
# EMAIL TOOL
# ---------------------------------------------
def send_booking_email(
    to_email: str,
    customer_name: str,
    appt_date: date,
    appt_time: str,
    booking_id: int,
    booking_type: str = None,
):
    try:
        host = settings.EMAIL_HOST
        port = settings.EMAIL_PORT
        user = settings.EMAIL_USER
        password = settings.EMAIL_PASSWORD.get_secret_value()
        from_name = settings.EMAIL_FROM_NAME
    except Exception as e:
        logger.error(f"Email configuration missing: {e}")
        return

    msg = EmailMessage()
    msg["Subject"] = f"Appointment Confirmation #{booking_id}"
    msg["From"] = f"{from_name} <{user}>"
    msg["To"] = to_email

    bt = booking_type or "Dental consultation"
    body = f"""
Hi {customer_name},

Your appointment has been booked successfully. 🎉

Booking details:
  • Booking ID : {booking_id}
  • Date       : {appt_date}
  • Time       : {appt_time}
  • Type       : {bt}
  • Clinic     : Smiles Dental Care

To respond to this booking:
  • To CONFIRM    : reply to this email with the word CONFIRM in the subject.
  • To CANCEL     : reply with CANCEL in the subject.
  • To RESCHEDULE : reply with RESCHEDULE in the subject and your preferred new time.

Best regards,
{from_name}
""".strip()

    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
    except Exception as e:
        logger.error(f"Failed to send email: {e}")


# ---------------------------------------------
# RAG TOOL helpers
# ---------------------------------------------
def ingest_pdfs_for_rag(user_id: str, uploaded_files):
    if not uploaded_files:
        return
    all_text = []
    
    for f in uploaded_files:
        # Save to local disk first for processing
        path = save_uploaded_file(user_id, f)
        
        # Save record to DB
        try:
            db_save_upload(user_id, path, f.name)
        except Exception as e:
            logger.error(f"Failed to save upload record: {e}")

        text = extract_pdf_text(path)
        if text.strip():
            all_text.append(text)

    if not all_text:
        st.warning("No readable text found in uploaded PDFs.")
        return

    if RAGPipeline:
        rp = RAGPipeline(user_id=user_id)
        combined = "\n\n".join(all_text)
        rp.build_index(combined)
        st.session_state.rag_index = rp
        st.success(f"RAG index built with {len(all_text)} documents ✅")
    else:
        st.info("RAG pipeline not available.")


# ---------------------------------------------
# Booking flow (multi-turn) and chat routing
# ---------------------------------------------
def reset_booking_flow():
    st.session_state.booking_flow = {
        "active": False,
        "slots": {
            "name": None,
            "email": None,
            "phone": None,
            "booking_type": None,
            "date": None,
            "time": None,
        },
        "awaiting_field": None,
        "booking_id": None,
    }

def detect_booking_intent(msg: str) -> bool:
    msg_l = msg.lower()
    keywords = ["book", "appointment", "schedule", "visit", "slot", "consultation"]
    return any(k in msg_l for k in keywords)

def parse_date_from_text(txt: str):
    txt = txt.strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(txt, fmt).date()
        except ValueError:
            continue
    return None

def parse_time_from_text(txt: str):
    txt = txt.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            t = datetime.strptime(txt, fmt).time()
            return t.strftime("%H:%M")
        except ValueError:
            continue
    return None

def summarize_booking_and_ask_confirm(slots):
    d = slots["date"]
    t = slots["time"]
    bt = slots["booking_type"]
    phone = slots["phone"] or "Not provided yet"
    name = slots["name"]
    email = slots["email"]

    summary = (
        "Here are your booking details:\n\n"
        f"• Name: **{name}**\n"
        f"• Email: **{email}**\n"
        f"• Phone: **{phone}**\n"
        f"• Type: **{bt}**\n"
        f"• Date: **{d.strftime('%Y-%m-%d')}**\n"
        f"• Time: **{t}**\n\n"
        "Please confirm to proceed:\n"
        "- Reply **yes** to confirm and save the booking\n"
        "- Reply **no** to cancel"
    )
    return summary

def run_booking_flow(user_message: str, user):
    bf = st.session_state.booking_flow
    slots = bf["slots"]

    if not bf["active"]:
        bf["active"] = True
        slots["name"] = user["name"]
        slots["email"] = user["email"]
        slots["phone"] = user.get("phone")
        bf["awaiting_field"] = "booking_type"
        return (
            "Great! Let's book an appointment. 🗓️\n\n"
            "What type of booking is this? (e.g., 'Root canal', 'Check-up', 'Cleaning')"
        )

    field = bf["awaiting_field"]
    msg = user_message.strip()

    if field == "booking_type":
        slots["booking_type"] = msg
        bf["awaiting_field"] = "date"
        return (
            f"Got it: **{msg}**.\n\n"
            "Please enter your preferred *date* in format `YYYY-MM-DD`."
        )

    if field == "date":
        parsed = parse_date_from_text(msg)
        if not parsed:
            return "I couldn't understand that date. Please enter date as `YYYY-MM-DD`."
        if parsed < date.today():
            return "The date seems to be in the past. Please enter a future date in `YYYY-MM-DD`."
        slots["date"] = parsed
        bf["awaiting_field"] = "time"
        return "Thanks! Now enter your preferred time in 24h format `HH:MM`."

    if field == "time":
        parsed = parse_time_from_text(msg)
        if not parsed:
            return "I couldn't understand that time. Please enter time as `HH:MM` (24-hour)."
        
        # Check conflict immediately
        if has_booking_conflict(slots["date"], parsed):
             return f"Sorry, the slot at {parsed} on {slots['date']} is already booked. Please choose a different time."

        slots["time"] = parsed
        bf["awaiting_field"] = "phone"
        if not slots["phone"]:
            return "Please share your phone number (digits only)."
        else:
            bf["awaiting_field"] = "confirm"
            return summarize_booking_and_ask_confirm(slots)

    if field == "phone":
        digits = "".join(ch for ch in msg if ch.isdigit())
        if len(digits) < 7:
            return "That doesn't look like a valid phone number. Please re-enter."
        slots["phone"] = digits
        bf["awaiting_field"] = "confirm"
        return summarize_booking_and_ask_confirm(slots)

    if field == "confirm":
        if msg.lower() in ["yes", "y", "confirm"]:
            try:
                booking_id = save_booking(
                    user_id=user["id"],
                    date=slots["date"],
                    time=slots["time"],
                    reason=f"{slots['booking_type']} (via chatbot)",
                    booking_type=slots["booking_type"]
                )
                
                if booking_id:
                    bf["booking_id"] = booking_id
                    
                    # Send email
                    send_booking_email(
                        to_email=slots["email"],
                        customer_name=slots["name"],
                        appt_date=slots["date"],
                        appt_time=slots["time"],
                        booking_id=booking_id,
                        booking_type=slots["booking_type"],
                    )

                    reset_booking_flow()
                    return (
                        f"✅ Your booking is confirmed!\n\n"
                        f"• Booking ID: **{booking_id}**\n"
                        f"• Date: {slots['date'].strftime('%Y-%m-%d')}\n"
                        f"• Time: {slots['time']}\n\n"
                        "I've also emailed you the confirmation. Anything else I can help you with?"
                    )
                else:
                    reset_booking_flow()
                    return "Something went wrong while saving your booking. Please try again later."
            except Exception as e:
                logger.error(f"Booking error: {e}")
                reset_booking_flow()
                return "An error occurred while processing your booking."

        elif msg.lower() in ["no", "n", "cancel"]:
            reset_booking_flow()
            return "Okay, I've cancelled this booking request. Let me know if you'd like to start again."
        else:
            return "Please reply with **yes** to confirm or **no** to cancel."

    return "I'm not sure which detail we're on. Let's start over. Say something like *'I want to book an appointment'*."


# ---------------------------------------------
# Pages
# ---------------------------------------------
def user_login_page():
    login_container = st.container()
    login_success = False

    with login_container:
        st.markdown('<div class="login-wrapper">', unsafe_allow_html=True)
        left, right = st.columns([1.1, 1])

        with left:
            st.markdown('<div class="login-card">', unsafe_allow_html=True)
            st.markdown('<div class="login-title">Sign in to Clinic Assistant</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-subtitle">Chat with the AI assistant, book appointments, upload reports.</div>', unsafe_allow_html=True)

            tab_login, tab_register = st.tabs(["Sign in", "Create account"])

            with tab_login:
                with st.form("user_login_form"):
                    email = st.text_input("Email address")
                    password = st.text_input("Password", type="password")
                    submitted = st.form_submit_button("Sign in")

                if submitted:
                    pw_hash = hash_password(password)
                    user = authenticate(email, pw_hash)
                    if user and user["role"] == "user":
                        st.session_state.user = user
                        st.session_state.chat_history = []
                        reset_booking_flow()
                        st.success(f"Welcome back, {user['name']}!")
                        login_success = True
                    elif user and user["role"] != "user":
                        st.error("This email belongs to an admin. Please use the Admin Login page.")
                    else:
                        st.error("Incorrect email or password.")

            with tab_register:
                with st.form("user_register_form"):
                    name = st.text_input("Full name")
                    email_reg = st.text_input("Email address")
                    password_reg = st.text_input("Password", type="password")
                    password_reg2 = st.text_input("Confirm password", type="password")
                    reg_submitted = st.form_submit_button("Create account")

                if reg_submitted:
                    if not name or not email_reg or not password_reg:
                        st.error("Please fill in all required fields.")
                    elif password_reg != password_reg2:
                        st.error("Passwords do not match.")
                    else:
                        pw_hash = hash_password(password_reg)
                        ok, err = create_user(name, email_reg, pw_hash)
                        if ok:
                            user = authenticate(email_reg, pw_hash)
                            if user:
                                st.session_state.user = user
                                st.session_state.chat_history = []
                                reset_booking_flow()
                                st.success("Account created! Redirecting...")
                                safe_rerun()
                            else:
                                st.success("Account created! Please sign in.")
                        else:
                            st.error(err or "Error creating account.")

            st.markdown('<div class="small-link">Admin? <a href="#">Use the Admin Login from the left menu.</a></div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

        with right:
            st.image('img1.jpg', width=400) # Fixed width or use_column_width=True (deprecated) -> use "auto" or just let it be

        st.markdown('</div>', unsafe_allow_html=True)

    if login_success and st.session_state.user is not None:
        login_container.empty()
        user_dashboard()


def admin_login_page():
    login_container = st.container()
    login_success = False

    with login_container:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown('<div class="login-title">Admin sign in</div>', unsafe_allow_html=True)

        with st.form("admin_login_form"):
            email = st.text_input("Admin email", value="admin@example.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign in as admin")

        if submitted:
            pw_hash = hash_password(password)
            user = authenticate(email, pw_hash)
            if user and user.get('role') == 'admin':
                st.session_state.user = user
                st.success(f"Welcome, {user['name']} (Admin)")
                login_success = True
            else:
                st.error("Invalid admin credentials.")

        st.markdown('</div>', unsafe_allow_html=True)

    if login_success and st.session_state.user is not None:
        login_container.empty()
        admin_dashboard()


def user_dashboard():
    user = st.session_state.user
    st.subheader(f"Hi {user['name']} 👋")
    
    col_left, col_right = st.columns([1, 2])

    # LEFT: Uploads (RAG only)
    with col_left:
        st.markdown('<div class="upload-box">', unsafe_allow_html=True)
        st.markdown("### 🔎 RAG Context")
        st.caption("Upload PDFs to give the AI more knowledge.")
        
        rag_pdfs = st.file_uploader("Add PDFs", type=['pdf'], accept_multiple_files=True, key='rag_upload')
        if rag_pdfs:
            ingest_pdfs_for_rag(user['id'], rag_pdfs)
            
        st.markdown('</div>', unsafe_allow_html=True)

    # RIGHT: Chat
    with col_right:
        st.markdown('### 💬 AI Booking Assistant')
        
        # Chat container
        chat_container = st.container(height=500)
        with chat_container:
            for msg in st.session_state.chat_history:
                with st.chat_message(msg['role']):
                    st.markdown(msg['content'])

        # Input
        user_input = st.chat_input("Type your message...")
        if user_input:
            # Add user message
            st.session_state.chat_history.append({'role': 'user', 'content': user_input})
            
            # Determine response
            bf = st.session_state.booking_flow
            if bf and bf.get('active'):
                bot_reply = run_booking_flow(user_input, user)
            elif detect_booking_intent(user_input):
                bot_reply = run_booking_flow(user_input, user)
            else:
                # RAG / Chat Engine
                if ChatEngine:
                    engine = ChatEngine()
                    rag_obj = st.session_state.get('rag_index')
                    rag_chunks = None
                    try:
                        if rag_obj and hasattr(rag_obj, 'retrieve'):
                            rag_chunks = rag_obj.retrieve(user_input)
                    except Exception:
                        pass
                    
                    bot_reply = engine.generate_answer(query=user_input, history=st.session_state.chat_history, rag_chunks=rag_chunks)
                else:
                    bot_reply = "I'm here to help you book appointments. Just say 'I want to book an appointment'. (AI Engine not available)"

            # Add bot message
            st.session_state.chat_history.append({'role': 'assistant', 'content': bot_reply})
            safe_rerun()


def admin_dashboard():
    """
    Redesigned Admin Dashboard - Fully Supabase-driven with 8 comprehensive sections
    """
    st.title("🎯 Admin Dashboard")
    st.markdown("**Smiles Dental Care** - Comprehensive Management Portal")
    st.markdown("---")
    
    # Import Supabase helpers
    from modules.supabase_client import (
        get_all_patients, get_all_doctors, get_all_bookings, 
        get_patient_uploads, get_frequent_patients, get_doctor_performance,
        update_booking_status, update_doctor_status
    )
    
    # Fetch all data
    patients = get_all_patients()
    doctors = get_all_doctors()
    bookings = get_all_bookings()
    uploads = get_patient_uploads()
    frequent = get_frequent_patients(limit=10)
    performance = get_doctor_performance()
    
    # --- 1. METRICS HEADER (7 Cards) ---
    st.markdown("### 📊 Key Metrics")
    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
    
    today = datetime.now().date()
    today_str = today.isoformat()
    bookings_today = [b for b in bookings if b.get("appt_date") == today_str]
    confirmed = [b for b in bookings if b.get("status") == "Confirmed"]
    pending = [b for b in bookings if b.get("status") == "Pending"]
    cancelled = [b for b in bookings if b.get("status") == "Cancelled"]
    
    with m1:
        st.metric("Total Patients", len(patients))
    with m2:
        st.metric("Total Doctors", len(doctors))
    with m3:
        st.metric("Total Bookings", len(bookings))
    with m4:
        st.metric("Confirmed", len(confirmed))
    with m5:
        st.metric("Pending", len(pending))
    with m6:
        st.metric("Today's Bookings", len(bookings_today))
    with m7:
        st.metric("Total Uploads", len(uploads))
    
    st.markdown("---")
    
    # --- 2. MAIN TABS ---
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "👥 Patients", "🩺 Doctors", "📅 Bookings", "📁 Documents", "📈 Analytics"
    ])
    
    # --- TAB 1: PATIENTS OVERVIEW ---
    with tab1:
        st.markdown("### 👥 Patients Overview")
        if patients:
            # Build patient dataframe with additional info
            patient_data = []
            for p in patients:
                from modules.supabase_client import get_patient_booking_count, get_patient_last_visit
                booking_count = get_patient_booking_count(p.get("id"))
                last_visit = get_patient_last_visit(p.get("id")) or "Never"
                patient_data.append({
                    "ID": p.get("id"),
                    "Name": p.get("name"),
                    "Email": p.get("email"),
                    "Phone": p.get("phone", "N/A"),
                    "Total Bookings": booking_count,
                    "Last Visit": last_visit,
                    "Registered": p.get("created_at", "")[:10] if p.get("created_at") else "N/A"
                })
            
            df_patients = pd.DataFrame(patient_data)
            st.dataframe(df_patients, use_container_width=True, hide_index=True)
            
            # Export CSV
            csv = df_patients.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Patients CSV", csv, "patients.csv", "text/csv")
        else:
            st.info("No patients registered yet.")
    
    # --- TAB 2: DOCTORS OVERVIEW ---
    with tab2:
        st.markdown("### 🩺 Doctors Overview")
        if doctors:
            # Build doctors dataframe with performance
            doctor_data = []
            perf_map = {d["id"]: d for d in performance}
            
            for doc in doctors:
                doc_id = doc.get("id")
                perf = perf_map.get(doc_id, {})
                doctor_data.append({
                    "ID": doc_id,
                    "Name": doc.get("name"),
                    "Email": doc.get("email"),
                    "Speciality": doc.get("speciality"),
                    "Phone": doc.get("phone", "N/A"),
                    "Status": doc.get("status", "available"),
                    "Total Appointments": perf.get("total_appointments", 0),
                    "Utilization %": perf.get("utilization_percent", 0.0)
                })
            
            df_doctors = pd.DataFrame(doctor_data)
            st.dataframe(df_doctors, use_container_width=True, hide_index=True)
            
            # Toggle doctor status
            st.markdown("#### Change Doctor Availability")
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                selected_doc = st.selectbox("Select Doctor", [d["Name"] for d in doctor_data])
            with col2:
                new_status = st.selectbox("New Status", ["available", "busy", "off-duty"])
            with col3:
                if st.button("Update"):
                    doc_id = next(d["ID"] for d in doctor_data if d["Name"] == selected_doc)
                    if update_doctor_status(doc_id, new_status):
                        st.success(f"✅ {selected_doc} status updated to {new_status}")
                        safe_rerun()
                    else:
                        st.error("❌ Failed to update doctor status")
            
            # Export CSV
            csv = df_doctors.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Doctors CSV", csv, "doctors.csv", "text/csv")
        else:
            st.info("No doctors registered yet.")
    
    # --- TAB 3: BOOKINGS OVERVIEW ---
    with tab3:
        st.markdown("### 📅 Bookings Overview")
        if bookings:
            # Build bookings dataframe
            booking_data = []
            for b in bookings:
                users = b.get("users", {})
                if isinstance(users, list) and users:
                    users = users[0]
                docs = b.get("doctors", {})
                if isinstance(docs, list) and docs:
                    docs = docs[0]
                
                booking_data.append({
                    "ID": b.get("id"),
                    "Patient": users.get("name", "Unknown") if users else "Unknown",
                    "Email": users.get("email", "N/A") if users else "N/A",
                    "Phone": users.get("phone", "N/A") if users else "N/A",
                    "Doctor": docs.get("name", "N/A") if docs else "N/A",
                    "Speciality": docs.get("speciality", "N/A") if docs else "N/A",
                    "Date": b.get("appt_date", "N/A"),
                    "Time": b.get("appt_time", "N/A"),
                    "Type": b.get("booking_type", "N/A"),
                    "Reason": b.get("reason", "N/A"),
                    "Status": b.get("status", "Pending")
                })
            
            df_bookings = pd.DataFrame(booking_data)
            
            # Filters
            st.markdown("#### 🔍 Filters")
            fc1, fc2, fc3, fc4 = st.columns(4)
            with fc1:
                status_filter = st.selectbox("Status", ["All"] + list(df_bookings["Status"].unique()))
            with fc2:
                date_filter = st.date_input("Date", value=None)
            with fc3:
                doctor_filter = st.selectbox("Doctor", ["All"] + list(df_bookings["Doctor"].unique()))
            with fc4:
                search = st.text_input("Search Patient")
            
            # Apply filters
            filtered = df_bookings.copy()
            if status_filter != "All":
                filtered = filtered[filtered["Status"] == status_filter]
            if date_filter:
                filtered = filtered[filtered["Date"] == date_filter.isoformat()]
            if doctor_filter != "All":
                filtered = filtered[filtered["Doctor"] == doctor_filter]
            if search:
                filtered = filtered[filtered["Patient"].str.contains(search, case=False, na=False)]
            
            st.dataframe(filtered, use_container_width=True, hide_index=True)
            
            # Update booking status
            st.markdown("#### Update Booking Status")
            uc1, uc2, uc3 = st.columns([2, 2, 1])
            with uc1:
                booking_id = st.number_input("Booking ID", min_value=1, step=1)
            with uc2:
                new_status = st.selectbox("New Status", ["Pending", "Confirmed", "Cancelled", "Completed"])
            with uc3:
                if st.button("Update Status"):
                    if update_booking_status(booking_id, new_status):
                        st.success(f"✅ Booking #{booking_id} updated to {new_status}")
                        safe_rerun()
                    else:
                        st.error("❌ Failed to update booking")
            
            # Export CSV
            csv = filtered.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Bookings CSV", csv, "bookings.csv", "text/csv")
        else:
            st.info("No bookings found.")
    
    # --- TAB 4: DOCUMENTS ---
    with tab4:
        st.markdown("### 📁 Uploaded Documents")
        if uploads:
            # Build uploads dataframe
            upload_data = []
            for u in uploads:
                users = u.get("users", {})
                if isinstance(users, list) and users:
                    users = users[0]
                
                upload_data.append({
                    "ID": u.get("id"),
                    "Patient": users.get("name", "Unknown") if users else "Unknown",
                    "Email": users.get("email", "N/A") if users else "N/A",
                    "File Name": u.get("original_name", "N/A"),
                    "File Type": u.get("file_type", "N/A"),
                    "File Path": u.get("file_path", "N/A"),
                    "Uploaded At": u.get("uploaded_at", "")[:19] if u.get("uploaded_at") else "N/A"
                })
            
            df_uploads = pd.DataFrame(upload_data)
            
            # Patient filter
            patient_emails = sorted(df_uploads["Email"].unique())
            selected_patient = st.selectbox("Filter by Patient", ["All"] + patient_emails)
            
            if selected_patient != "All":
                df_uploads = df_uploads[df_uploads["Email"] == selected_patient]
            
            st.dataframe(df_uploads, use_container_width=True, hide_index=True)
            
            # Export CSV
            csv = df_uploads.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Documents CSV", csv, "documents.csv", "text/csv")
        else:
            st.info("No documents uploaded yet.")
    
    # --- TAB 5: ANALYTICS ---
    with tab5:
        st.markdown("### 📈 Analytics Dashboard")
        
        # Section A: Frequent Patients
        st.markdown("#### 🏆 Top 10 Frequent Patients")
        if frequent:
            freq_data = pd.DataFrame(frequent)
            st.dataframe(freq_data, use_container_width=True, hide_index=True)
            
            # Bar chart
            st.bar_chart(freq_data.set_index("name")["visit_count"], use_container_width=True)
        else:
            st.info("No patient visit data available.")
        
        st.markdown("---")
        
        # Section B: Doctor Performance
        st.markdown("#### 🩺 Doctor Performance")
        if performance:
            perf_data = pd.DataFrame(performance)
            st.dataframe(perf_data, use_container_width=True, hide_index=True)
            
            # Bar chart: Total appointments per doctor
            st.markdown("**Total Appointments by Doctor**")
            st.bar_chart(perf_data.set_index("name")["total_appointments"], use_container_width=True)
            
            # Line chart: Utilization %
            st.markdown("**Utilization % by Doctor**")
            st.line_chart(perf_data.set_index("name")["utilization_percent"], use_container_width=True)
        else:
            st.info("No doctor performance data available.")
        
        st.markdown("---")
        
        # Section C: Bookings Status Distribution
        st.markdown("#### 📊 Bookings Status Distribution")
        if bookings:
            from collections import Counter
            status_counts = Counter(b.get("status", "Unknown") for b in bookings)
            status_df = pd.DataFrame(status_counts.items(), columns=["Status", "Count"])
            
            st.dataframe(status_df, use_container_width=True, hide_index=True)
            st.bar_chart(status_df.set_index("Status")["Count"], use_container_width=True)
        else:
            st.info("No booking status data.")
        
        st.markdown("---")
        
        # Section D: Daily Bookings Trend (Last 30 days)
        st.markdown("#### 📅 Daily Bookings Trend (Last 30 Days)")
        if bookings:
            # Build daily counts
            from collections import defaultdict
            daily_counts = defaultdict(int)
            for b in bookings:
                appt_date = b.get("appt_date")
                if appt_date:
                    daily_counts[appt_date] += 1
            
            # Sort by date
            sorted_dates = sorted(daily_counts.items())
            trend_df = pd.DataFrame(sorted_dates, columns=["Date", "Bookings"])
            
            # Last 30 days
            if len(trend_df) > 30:
                trend_df = trend_df.tail(30)
            
            st.line_chart(trend_df.set_index("Date")["Bookings"], use_container_width=True)
        else:
            st.info("No trend data available.")


# ---------------------------------------------
# Main Router
# ---------------------------------------------
def main():
    if st.session_state.user:
        if st.session_state.user.get("role") == "admin":
            admin_dashboard()
        else:
            user_dashboard()
        
        if st.sidebar.button("Logout"):
            st.session_state.user = None
            st.session_state.chat_history = []
            reset_booking_flow()
            safe_rerun()
    else:
        # Sidebar navigation for login
        page = st.sidebar.radio("Navigation", ["Patient Login", "Admin Login"])
        if page == "Patient Login":
            user_login_page()
        else:
            admin_login_page()

if __name__ == "__main__":
    main()
