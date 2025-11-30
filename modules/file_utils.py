import os
import PyPDF2
from datetime import datetime

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def save_uploaded_file(user_id, file):
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    # Sanitize and truncate filename to avoid "Invalid argument" errors (Windows max path is 260 chars)
    safe_name = "".join(c for c in file.name if c.isalnum() or c in "._- ")
    if len(safe_name) > 50:
        safe_name = safe_name[-50:]
        
    filename = f"{user_id}_{ts}_{safe_name}"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(file.getbuffer())

    return path

def extract_pdf_text(path):
    text = ""
    with open(path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for p in reader.pages:
            content = p.extract_text()
            if content:
                text += content + "\n"
    return text.strip()
