import pandas as pd
from datetime import date
from typing import List, Dict, Any

def calculate_admin_metrics(bookings_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates key metrics for the admin dashboard.
    """
    if bookings_df.empty:
        return {
            "total_bookings": 0,
            "upcoming_bookings": 0,
            "bookings_today": 0,
            "unique_patients": 0
        }

    today_str = date.today().isoformat()
    
    # Ensure appt_date is string for comparison if not already
    if not pd.api.types.is_string_dtype(bookings_df['appt_date']):
        bookings_df['appt_date'] = bookings_df['appt_date'].astype(str)

    total_bookings = len(bookings_df)
    bookings_today = bookings_df[bookings_df['appt_date'] == today_str].shape[0]
    upcoming_bookings = bookings_df[bookings_df['appt_date'] >= today_str].shape[0]
    unique_patients = bookings_df['email'].nunique() if 'email' in bookings_df.columns else 0

    return {
        "total_bookings": total_bookings,
        "upcoming_bookings": upcoming_bookings,
        "bookings_today": bookings_today,
        "unique_patients": unique_patients
    }

def get_frequent_patients(bookings_df: pd.DataFrame, top_n: int = 5) -> pd.DataFrame:
    """
    Returns a DataFrame of top patients by booking count.
    """
    if bookings_df.empty or 'email' not in bookings_df.columns:
        return pd.DataFrame()

    # Group by email and name, count bookings
    top_patients = bookings_df.groupby(['email', 'name'])['booking_id'].count().reset_index(name='visit_count')
    top_patients = top_patients.sort_values('visit_count', ascending=False).head(top_n)
    return top_patients

def get_bookings_per_day(bookings_df: pd.DataFrame) -> pd.DataFrame:
    """
    Returns a DataFrame of booking counts per day.
    """
    if bookings_df.empty or 'appt_date' not in bookings_df.columns:
        return pd.DataFrame()

    counts = bookings_df.groupby('appt_date')['booking_id'].count().reset_index(name='count')
    counts = counts.sort_values('appt_date')
    return counts
