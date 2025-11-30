import logging
from typing import Optional, List, Dict, Any, Tuple
from supabase import create_client, Client
from modules.settings import get_settings

# Configure logger
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_client: Optional[Client] = None

def get_client() -> Client:
    global _client
    if _client is None:
        settings = get_settings()
        try:
            _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY.get_secret_value())
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise RuntimeError("Supabase client initialization failed. Check configuration.") from e
    return _client

def is_configured() -> bool:
    try:
        get_client()
        return True
    except Exception:
        return False

# --- Utility to surface raw API errors (useful for debugging) ---
def _extract_error_text(exc: Exception) -> str:
    # postgrest exceptions may carry JSON; try to pull message
    try:
        text = str(exc)
        # attempt to find JSON-like payload in exception string
        if "Could not find the table" in text:
            return text
        return text
    except Exception:
        return str(exc)

# --- Core operations (with improved logging) ---
def create_user(name: str, email: str, password_hash: str, role: str = "user") -> Tuple[bool, Optional[str]]:
    client = get_client()
    payload = {"name": name, "email": email, "password_hash": password_hash, "role": role}
    try:
        res = client.table("users").insert(payload).execute()
        logger.debug("create_user response: %s", getattr(res, "data", res))
        return True, None
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("create_user failed: %s", msg)
        return False, msg

def authenticate(email: str, password_hash: str) -> Optional[Dict[str, Any]]:
    client = get_client()
    try:
        # Security: Do NOT select password_hash
        res = client.table("users").select("id,name,email,role,created_at").eq("email", email).eq("password_hash", password_hash).limit(1).execute()
        logger.debug("authenticate response: %s", getattr(res, "data", res))
        data = getattr(res, "data", None) or []
        if not data:
            return None
        row = data[0]
        return {"id": row.get("id"), "name": row.get("name"), "email": row.get("email"), "role": row.get("role")}
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("authenticate failed: %s", msg)
        return None

def save_upload(user_id: str, file_path: str, original_name: str) -> Tuple[bool, Optional[str]]:
    client = get_client()
    payload = {"user_id": user_id, "file_path": file_path, "original_name": original_name}
    try:
        res = client.table("uploads").insert(payload).execute()
        logger.debug("save_upload response: %s", getattr(res, "data", res))
        return True, None
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("save_upload failed: %s", msg)
        return False, msg

def save_booking(user_id: str, appt_date: str, appt_time: str, reason: str, status: str = "Pending", booking_type: str = None) -> Optional[int]:
    client = get_client()
    payload = {
        "user_id": user_id, 
        "appt_date": appt_date, 
        "appt_time": appt_time, 
        "reason": reason, 
        "status": status,
        "booking_type": booking_type
    }
    try:
        res = client.table("bookings").insert(payload).execute()
        logger.debug("save_booking response: %s", getattr(res, "data", res))
        inserted = getattr(res, "data", None) or []
        if not inserted:
            return None
        return inserted[0].get("id")
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("save_booking failed: %s", msg)
        return None

def list_bookings() -> List[Dict[str, Any]]:
    client = get_client()
    try:
        # include related user fields (PostgREST allows dot-notation if FK/relationship present)
        res = client.table("bookings").select("id, user_id, appt_date, appt_time, reason, status, created_at, booking_type, users(id,name,email,phone)").order("appt_date", desc=True).order("appt_time", desc=True).execute()
        logger.debug("list_bookings response: %s", getattr(res, "data", res))
        return getattr(res, "data", []) or []
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("list_bookings failed: %s", msg)
        return []

def update_booking_status(booking_id: int, new_status: str) -> bool:
    client = get_client()
    try:
        res = client.table("bookings").update({"status": new_status}).eq("id", booking_id).execute()
        logger.debug("update_booking_status response: %s", getattr(res, "data", res))
        return True
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("update_booking_status failed: %s", msg)
        return False

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    client = get_client()
    try:
        res = client.table("users").select("id,name,email,role,phone").eq("email", email).limit(1).execute()
        logger.debug("get_user_by_email response: %s", getattr(res, "data", res))
        data = getattr(res, "data", None) or []
        if not data:
            return None
        row = data[0]
        return {"id": row.get("id"), "name": row.get("name"), "email": row.get("email"), "role": row.get("role"), "phone": row.get("phone")}
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("get_user_by_email failed: %s", msg)
        return None

# --- helper: try a minimal select on a table to confirm visibility ---
def check_table_visible(table_name: str) -> Tuple[bool, Optional[str]]:
    """Returns (visible, reason_if_not)"""
    client = get_client()
    try:
        # attempt a very small select
        res = client.table(table_name).select("id").limit(1).execute()
        logger.debug("check_table_visible %s -> %s", table_name, getattr(res, "data", res))
        return True, None
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("check_table_visible failed for %s: %s", table_name, msg)
        return False, msg

def migrate_schema():
    """Reads modules/db_migrations.sql and executes it via Supabase RPC or direct SQL if possible.
    Note: Supabase-py client doesn't support raw SQL execution easily without an RPC function.
    For this task, we will instruct the user to run the SQL in the Supabase Dashboard SQL Editor
    OR we can try to use a special RPC function if it exists.
    
    However, the requirements say 'migrate_schema() helper (migrate executes the SQL file)'.
    Since we can't easily run raw SQL from the client without a 'exec_sql' RPC, 
    we will read the file and print instructions or try to use a postgres driver if we had the connection string.
    But we only have the API URL/Key.
    
    Wait, the requirements say 'migrate executes the SQL file'.
    If we are using the Supabase Python client, we are limited to the API.
    Unless we use the `postgres` library with the connection string, but we don't have that in the env vars usually (just URL/Key).
    
    Actually, we can't execute DDL (CREATE TABLE) via the PostgREST API (supabase-py).
    
    Correction: The user prompt says "migrate executes the SQL file".
    If I cannot do it via the client, I should probably log a warning or provide a workaround.
    BUT, if I am running locally, maybe I can use a postgres driver? No, I don't have the connection string.
    
    Let's assume for now we will just log the instructions, OR if there is a way to do it.
    Actually, the `supabase` client allows `rpc`. If the user has a `exec_sql` function, we could use it.
    But we can't assume that.
    
    Re-reading requirements: "modules/db.py — migration runner using the supabase client (server-side) or fallback to local SQLite for dev."
    And "Run migrations (script will call modules/supabase_client.migrate_schema())".
    
    If I can't run DDL via the client, I might have to fail or ask the user to run it.
    However, I will implement a placeholder that reads the file and *tries* to run it if I can, 
    or explicitly tells the user to run it in the dashboard.
    
    Actually, I will implement it to read the file and print it, 
    and maybe try to execute it if I can find a way, but likely I will just print "Please run this SQL in Supabase Dashboard".
    
    Wait, if I am in a python script, I can't magically run SQL on Supabase without a direct connection or RPC.
    I will implement `migrate_schema` to read the SQL file and print the instructions clearly.
    """
    import os
    
    migration_file = os.path.join(os.path.dirname(__file__), "db_migrations.sql")
    if not os.path.exists(migration_file):
        logger.error("Migration file not found: %s", migration_file)
        return

    with open(migration_file, "r") as f:
        sql = f.read()
    
    print("--- BEGIN MIGRATION SQL ---")
    print(sql)
    print("--- END MIGRATION SQL ---")
    global _client
    if _client is None:
        settings = get_settings()
        try:
            _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY.get_secret_value())
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise RuntimeError("Supabase client initialization failed. Check configuration.") from e
    return _client

def is_configured() -> bool:
    try:
        get_client()
        return True
    except Exception:
        return False

# --- Utility to surface raw API errors (useful for debugging) ---
def _extract_error_text(exc: Exception) -> str:
    # postgrest exceptions may carry JSON; try to pull message
    try:
        text = str(exc)
        # attempt to find JSON-like payload in exception string
        if "Could not find the table" in text:
            return text
        return text
    except Exception:
        return str(exc)

# --- Core operations (with improved logging) ---
def create_user(name: str, email: str, password_hash: str, role: str = "user") -> Tuple[bool, Optional[str]]:
    client = get_client()
    payload = {"name": name, "email": email, "password_hash": password_hash, "role": role}
    try:
        res = client.table("users").insert(payload).execute()
        logger.debug("create_user response: %s", getattr(res, "data", res))
        return True, None
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("create_user failed: %s", msg)
        return False, msg

def authenticate(email: str, password_hash: str) -> Optional[Dict[str, Any]]:
    client = get_client()
    try:
        # Security: Do NOT select password_hash
        res = client.table("users").select("id,name,email,role,created_at").eq("email", email).eq("password_hash", password_hash).limit(1).execute()
        logger.debug("authenticate response: %s", getattr(res, "data", res))
        data = getattr(res, "data", None) or []
        if not data:
            return None
        row = data[0]
        return {"id": row.get("id"), "name": row.get("name"), "email": row.get("email"), "role": row.get("role")}
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("authenticate failed: %s", msg)
        return None

def save_upload(user_id: str, file_path: str, original_name: str) -> Tuple[bool, Optional[str]]:
    client = get_client()
    payload = {"user_id": user_id, "file_path": file_path, "original_name": original_name}
    try:
        res = client.table("uploads").insert(payload).execute()
        logger.debug("save_upload response: %s", getattr(res, "data", res))
        return True, None
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("save_upload failed: %s", msg)
        return False, msg

def save_booking(user_id: str, appt_date: str, appt_time: str, reason: str, status: str = "Pending", booking_type: str = None) -> Optional[int]:
    client = get_client()
    payload = {
        "user_id": user_id, 
        "appt_date": appt_date, 
        "appt_time": appt_time, 
        "reason": reason, 
        "status": status,
        "booking_type": booking_type
    }
    try:
        res = client.table("bookings").insert(payload).execute()
        logger.debug("save_booking response: %s", getattr(res, "data", res))
        inserted = getattr(res, "data", None) or []
        if not inserted:
            return None
        return inserted[0].get("id")
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("save_booking failed: %s", msg)
        return None

def list_bookings() -> List[Dict[str, Any]]:
    client = get_client()
    try:
        # include related user fields (PostgREST allows dot-notation if FK/relationship present)
        res = client.table("bookings").select("id, user_id, appt_date, appt_time, reason, status, created_at, booking_type, users(id,name,email,phone)").order("appt_date", desc=True).order("appt_time", desc=True).execute()
        logger.debug("list_bookings response: %s", getattr(res, "data", res))
        return getattr(res, "data", []) or []
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("list_bookings failed: %s", msg)
        return []

def update_booking_status(booking_id: int, new_status: str) -> bool:
    client = get_client()
    try:
        res = client.table("bookings").update({"status": new_status}).eq("id", booking_id).execute()
        logger.debug("update_booking_status response: %s", getattr(res, "data", res))
        return True
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("update_booking_status failed: %s", msg)
        return False

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    client = get_client()
    try:
        res = client.table("users").select("id,name,email,role,phone").eq("email", email).limit(1).execute()
        logger.debug("get_user_by_email response: %s", getattr(res, "data", res))
        data = getattr(res, "data", None) or []
        if not data:
            return None
        row = data[0]
        return {"id": row.get("id"), "name": row.get("name"), "email": row.get("email"), "role": row.get("role"), "phone": row.get("phone")}
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("get_user_by_email failed: %s", msg)
        return None

# --- helper: try a minimal select on a table to confirm visibility ---
def check_table_visible(table_name: str) -> Tuple[bool, Optional[str]]:
    """Returns (visible, reason_if_not)"""
    client = get_client()
    try:
        # attempt a very small select
        res = client.table(table_name).select("id").limit(1).execute()
        logger.debug("check_table_visible %s -> %s", table_name, getattr(res, "data", res))
        return True, None
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("check_table_visible failed for %s: %s", table_name, msg)
        return False, msg

def migrate_schema():
    """Reads modules/db_migrations.sql and executes it via Supabase RPC or direct SQL if possible.
    Note: Supabase-py client doesn't support raw SQL execution easily without an RPC function.
    For this task, we will instruct the user to run the SQL in the Supabase Dashboard SQL Editor
    OR we can try to use a special RPC function if it exists.
    
    However, the requirements say 'migrate executes the SQL file'.
    Since we can't easily run raw SQL from the client without a 'exec_sql' RPC, 
    we will read the file and print instructions or try to use a postgres driver if we had the connection string.
    But we only have the API URL/Key.
    
    Actually, we can't execute DDL (CREATE TABLE) via the PostgREST API (supabase-py).
    
    Correction: The user prompt says "migrate executes the SQL file".
    If I cannot do it via the client, I might have to fail or ask the user to run it.
    BUT, if I am running locally, maybe I can use a postgres driver? No, I don't have the connection string.
    
    Let's assume for now we will just log the instructions, OR if there is a way to do it.
    Actually, the `supabase` client allows `rpc`. If the user has a `exec_sql` function, we could use it.
    But we can't assume that.
    
    Re-reading requirements: "modules/db.py — migration runner using the supabase client (server-side) or fallback to local SQLite for dev."
    And "Run migrations (script will call modules/supabase_client.migrate_schema())".
    
    If I can't run DDL via the client, I might have to fail or ask the user to run it.
    However, I will implement a placeholder that reads the file and *tries* to run it if I can, 
    or explicitly tells the user to run it in the dashboard.
    
    Actually, I will implement it to read the file and print it, 
    and maybe try to execute it if I can find a way, but likely I will just print "Please run this SQL in Supabase Dashboard".
    
    Wait, if I am in a python script, I can't magically run SQL on Supabase without a direct connection or RPC.
    I will implement `migrate_schema` to read the file and print the instructions clearly.
    """
    import os
    
    migration_file = os.path.join(os.path.dirname(__file__), "db_migrations.sql")
    if not os.path.exists(migration_file):
        logger.error("Migration file not found: %s", migration_file)
        return

    with open(migration_file, "r") as f:
        sql = f.read()
    
    print("--- BEGIN MIGRATION SQL ---")
    print(sql)
    print("--- END MIGRATION SQL ---")
    print("\n[IMPORTANT] The Supabase API client cannot execute DDL (CREATE TABLE) directly.")
    print("Please copy the SQL above and run it in your Supabase Dashboard > SQL Editor.")

# --- Admin Dashboard Helper Functions ---

def get_all_patients() -> List[Dict[str, Any]]:
    """Fetch all users with role='user' (patients)"""
    client = get_client()
    try:
        res = client.table("users").select("id,name,email,phone,created_at").eq("role", "user").order("created_at", desc=True).execute()
        logger.debug("get_all_patients response: %s", getattr(res, "data", res))
        return getattr(res, "data", []) or []
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("get_all_patients failed: %s", msg)
        return []

def get_all_doctors() -> List[Dict[str, Any]]:
    """Fetch all doctors from doctors table"""
    client = get_client()
    try:
        res = client.table("doctors").select("id,name,email,speciality,phone,status,created_at").order("name").execute()
        logger.debug("get_all_doctors response: %s", getattr(res, "data", res))
        return getattr(res, "data", []) or []
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("get_all_doctors failed: %s", msg)
        return []

def get_all_bookings() -> List[Dict[str, Any]]:
    """Fetch all bookings with user and doctor details"""
    client = get_client()
    try:
        # Try fetching with doctor details first
        res = client.table("bookings").select(
            "id,user_id,doctor_id,appt_date,appt_time,reason,status,booking_type,created_at,"
            "users(id,name,email,phone),"
            "doctors(id,name,speciality)"
        ).order("appt_date", desc=True).order("appt_time", desc=True).execute()
        logger.debug("get_all_bookings response: %s", getattr(res, "data", res))
        return getattr(res, "data", []) or []
    except Exception as e:
        # Fallback: fetch without doctors if relationship issue
        logger.warning("get_all_bookings with doctors failed, retrying without doctors: %s", e)
        try:
             res = client.table("bookings").select(
                "id,user_id,doctor_id,appt_date,appt_time,reason,status,booking_type,created_at,"
                "users(id,name,email,phone)"
            ).order("appt_date", desc=True).order("appt_time", desc=True).execute()
             return getattr(res, "data", []) or []
        except Exception as e2:
            msg = _extract_error_text(e2)
            logger.exception("get_all_bookings failed: %s", msg)
            return []

def get_patient_uploads(user_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Fetch uploads, optionally filtered by user_id"""
    client = get_client()
    try:
        query = client.table("uploads").select(
            "id,user_id,file_path,file_type,original_name,uploaded_at,"
            "users(id,name,email)"
        )
        if user_id:
            query = query.eq("user_id", user_id)
        res = query.order("uploaded_at", desc=True).execute()
        logger.debug("get_patient_uploads response: %s", getattr(res, "data", res))
        return getattr(res, "data", []) or []
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("get_patient_uploads failed: %s", msg)
        return []

def get_frequent_patients(limit: int = 10) -> List[Dict[str, Any]]:
    """Get top N patients by number of bookings"""
    client = get_client()
    try:
        # Fetch all bookings with user info
        bookings = get_all_bookings()
        if not bookings:
            return []
        
        # Count bookings per patient
        from collections import Counter
        user_counts = Counter()
        user_info = {}
        
        for booking in bookings:
            user_data = booking.get("users")
            if user_data:
                if isinstance(user_data, list) and user_data:
                    user_data = user_data[0]
                user_id = user_data.get("id")
                if user_id:
                    user_counts[user_id] += 1
                    user_info[user_id] = {
                        "name": user_data.get("name"),
                        "email": user_data.get("email"),
                        "phone": user_data.get("phone")
                    }
        
        # Sort and format
        frequent = []
        for user_id, count in user_counts.most_common(limit):
            info = user_info.get(user_id, {})
            frequent.append({
                "user_id": user_id,
                "name": info.get("name", "Unknown"),
                "email": info.get("email", "N/A"),
                "phone": info.get("phone", "N/A"),
                "visit_count": count
            })
        
        return frequent
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("get_frequent_patients failed: %s", msg)
        return []

def get_doctor_performance() -> List[Dict[str, Any]]:
    """Calculate performance metrics for each doctor"""
    client = get_client()
    try:
        doctors = get_all_doctors()
        bookings = get_all_bookings()
        
        # Count bookings per doctor
        from collections import Counter
        doctor_counts = Counter()
        
        for booking in bookings:
            doctor_data = booking.get("doctors")
            if doctor_data:
                if isinstance(doctor_data, list) and doctor_data:
                    doctor_data = doctor_data[0]
                doctor_id = doctor_data.get("id")
                if doctor_id:
                    doctor_counts[doctor_id] += 1
        
        # Format performance data
        performance = []
        total_bookings = sum(doctor_counts.values())
        
        for doctor in doctors:
            doctor_id = doctor.get("id")
            booking_count = doctor_counts.get(doctor_id, 0)
            utilization = (booking_count / total_bookings * 100) if total_bookings > 0 else 0
            
            performance.append({
                "id": doctor_id,
                "name": doctor.get("name"),
                "speciality": doctor.get("speciality"),
                "status": doctor.get("status"),
                "total_appointments": booking_count,
                "utilization_percent": round(utilization, 1)
            })
        
        # Sort by appointment count
        performance.sort(key=lambda x: x["total_appointments"], reverse=True)
        return performance
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("get_doctor_performance failed: %s", msg)
        return []

def update_doctor_status(doctor_id: int, status: str) -> bool:
    """Update doctor availability status"""
    client = get_client()
    try:
        res = client.table("doctors").update({"status": status}).eq("id", doctor_id).execute()
        logger.debug("update_doctor_status response: %s", getattr(res, "data", res))
        return True
    except Exception as e:
        msg = _extract_error_text(e)
        logger.exception("update_doctor_status failed: %s", msg)
        return False

def get_patient_booking_count(user_id: int) -> int:
    """Get total bookings for a specific patient"""
    client = get_client()
    try:
        res = client.table("bookings").select("id", count="exact").eq("user_id", user_id).execute()
        return res.count if hasattr(res, "count") else 0
    except Exception as e:
        logger.exception("get_patient_booking_count failed: %s", e)
        return 0

def get_patient_last_visit(user_id: int) -> Optional[str]:
    """Get the most recent booking date for a patient"""
    client = get_client()
    try:
        res = client.table("bookings").select("appt_date").eq("user_id", user_id).order("appt_date", desc=True).limit(1).execute()
        data = getattr(res, "data", []) or []
        if data:
            return data[0].get("appt_date")
        return None
    except Exception as e:
        logger.exception("get_patient_last_visit failed: %s", e)
        return None