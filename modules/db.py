import logging
from typing import Optional, Tuple, Any, Dict, List
from datetime import datetime
from . import supabase_client

logger = logging.getLogger(__name__)

# Re-export functions from supabase_client to maintain compatibility where possible
# or redirect calls to it.

def init_db():
    """
    Initializes the database.
    For Supabase, this might mean checking connection or running migrations if we could.
    For now, we just check configuration.
    """
    if not supabase_client.is_configured():
        logger.warning("Supabase is NOT configured. Database operations will fail.")
    else:
        logger.info("Supabase is configured.")

def create_user(name: str, email: str, pw_hash: str, role: str = "user") -> Tuple[bool, Optional[str]]:
    return supabase_client.create_user(name, email, pw_hash, role)

def authenticate(email: str, pw_hash: str) -> Optional[Dict[str, Any]]:
    return supabase_client.authenticate(email, pw_hash)

def save_booking(user_id: str, date: Any, time: str, reason: str, booking_type: str = None) -> Optional[int]:
    # Ensure date is string
    appt_date = date.isoformat() if hasattr(date, 'isoformat') else str(date)
    return supabase_client.save_booking(user_id, appt_date, time, reason, booking_type=booking_type)

def save_upload(user_id: str, file_path: str, original_name: str) -> None:
    ok, err = supabase_client.save_upload(user_id, file_path, original_name)
    if not ok:
        raise RuntimeError(f"Supabase upload save failed: {err}")

def list_bookings() -> List[Dict[str, Any]]:
    return supabase_client.list_bookings()

def update_booking_status(booking_id: int, new_status: str) -> bool:
    return supabase_client.update_booking_status(booking_id, new_status)

def get_conn():
    """
    Deprecated: Returns None as we are using Supabase API.
    Kept for compatibility if any legacy code calls it, but should be removed.
    """
    raise NotImplementedError("Direct DB connection is deprecated. Use supabase_client methods.")
