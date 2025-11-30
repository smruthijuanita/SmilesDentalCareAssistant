EMERGENCY_KEYWORDS = [
    "bleeding a lot",
    "cannot stop bleeding",
    "severe bleeding",
    "difficulty breathing",
    "can't breathe",
    "jaw fracture",
    "broken jaw",
    "unconscious",
    "swelling spreading",
    "severe trauma",
    "high fever",
]

def is_emergency(text: str) -> bool:
    t = text.lower()
    return any(kw in t for kw in EMERGENCY_KEYWORDS)

def emergency_response() -> str:
    return (
        "**⚠️ This may be an emergency.**\n\n"
        "I am not a substitute for a dentist or emergency care.\n"
        "Please **go to the nearest emergency department** or **call emergency services immediately.**"
    )
