from datetime import datetime, date
from modules.db import save_booking
from datetime import datetime
from modules.db import save_booking
from modules.email_utils import send_booking_email  # 👈 new import

def init_flow(user):
    return {
        "step": "phone",
        "name": user["name"],
        "email": user["email"],
        "phone": None,
        "date": None,
        "time": None,
        "reason": None
    }

def parse_date(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").date(), None
    except:
        return None, "Please enter date as YYYY-MM-DD."

def parse_time(t):
    try:
        return datetime.strptime(t, "%H:%M").time(), None
    except:
        return None, "Use HH:MM 24-hour format."

def handle_booking_msg(msg, flow, user):
    m = msg.lower()

    # Cancel at any time
    if m in ["cancel", "stop", "exit"]:
        return "Booking cancelled.", None

    step = flow["step"]

    if step == "phone":
        flow["phone"] = msg
        flow["step"] = "date"
        return "Enter preferred date (YYYY-MM-DD):", flow

    if step == "date":
        d, err = parse_date(msg)
        if err:
            return err, flow
        flow["date"] = d
        flow["step"] = "time"
        return "Enter preferred time (HH:MM):", flow

    if step == "time":
        t, err = parse_time(msg)
        if err:
            return err, flow
        flow["time"] = t
        flow["step"] = "reason"
        return "Briefly describe your reason for visit:", flow

    if step == "reason":
        flow["reason"] = msg
        flow["step"] = "confirm"
        summary = (
            f"Here is your booking summary:\n"
            f"- Name: {flow['name']}\n"
            f"- Email: {flow['email']}\n"
            f"- Phone: {flow['phone']}\n"
            f"- Date: {flow['date']}\n"
            f"- Time: {flow['time']}\n"
            f"- Reason: {flow['reason']}\n\n"
            "Type 'confirm' to finalize or 'cancel' to cancel."
        )
        return summary, flow

    if step == "confirm":
        if m == "confirm":
            bid = save_booking(
                user["id"],
                flow["date"],
                flow["time"].strftime("%H:%M"),
                f"Phone: {flow['phone']}\nReason: {flow['reason']}"
            )

            # Sending Confirmation Email using SMTP 
            try:
                send_booking_email(
                    to_email=user["email"],
                    customer_name=user["name"],
                    appt_date=flow["date"],
                    appt_time=flow["time"].strftime("%H:%M"),
                    booking_id=bid,
                )
                extra = " A confirmation email has been sent to you."
            except Exception as e:
                extra = f" (Booking saved, but email failed: {e})"

            return f"🎉 Appointment booked! Your booking ID is #{bid}.{extra}", None