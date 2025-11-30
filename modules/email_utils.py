import smtplib
from email.message import EmailMessage
from datetime import date
import logging
from modules.settings import get_settings

logger = logging.getLogger(__name__)

def send_booking_email(to_email: str, customer_name: str, appt_date, appt_time: str, booking_id: int):
    """
    Sends a booking confirmation email using settings from modules/settings.py.
    """
    settings = get_settings()
    
    host = settings.EMAIL_HOST
    port = settings.EMAIL_PORT
    user = settings.EMAIL_USER
    password = settings.EMAIL_PASSWORD.get_secret_value() if settings.EMAIL_PASSWORD else None
    from_name = settings.EMAIL_FROM_NAME

    if not password:
        logger.error("Email password not configured. Cannot send email.")
        return

    msg = EmailMessage()
    msg["Subject"] = f"Appointment Confirmation #{booking_id}"
    msg["From"] = f"{from_name} <{user}>"
    msg["To"] = to_email

    body = f"""
Hi {customer_name},

Your appointment has been booked successfully.

Booking details:
- Booking ID: {booking_id}
- Date: {appt_date}
- Time: {appt_time}
- Clinic: Smiles Dental Care

If you need to reschedule or cancel, please reply to this email.

Best regards,
{from_name}
""".strip()

    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        logger.info(f"Booking confirmation email sent to {to_email}")
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
