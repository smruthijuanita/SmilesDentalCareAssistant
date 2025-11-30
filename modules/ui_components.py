import streamlit as st
import os

def inject_css():
    st.markdown(
        """
        <style>
        div[data-testid="stTabs"] {
            background-color: transparent !important;
        }
        div[data-testid="stTabs"] > div > div {
            background-color: transparent !important;
        }
        button[data-baseweb="tab"] {
            background-color: transparent !important;
            color: #6b7280 !important;
        }
        button[data-baseweb="tab"][aria-selected="true"] {
            background-color: transparent !important;
            color: #2563eb !important;
            border-bottom: 2px solid #2563eb !important;
        }
        .main .block-container {
            background-color: transparent !important;
            max-width: 1200px;
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        .stApp {
            background: radial-gradient(circle at top, #e0f2fe 0, #f9fafb 45%, #f3f4f6 100%) !important;
        }
        .login-wrapper {
            display: flex;
            gap: 2rem;
            align-items: stretch;
        }
        .login-card {
            background: rgba(255,255,255,0.9);
            padding: 2rem;
            border-radius: 1.25rem;
            box-shadow: 0 18px 45px rgba(15,23,42,0.15);
        }
        .login-title {
            font-size: 1.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }
        .login-subtitle {
            font-size: 0.9rem;
            color: #6b7280;
            margin-bottom: 1rem;
        }
        .divider {
            text-align: center;
            margin: 1rem 0;
            font-size: 0.8rem;
            color: #9ca3af;
            position: relative;
        }
        .divider::before,
        .divider::after {
            content: "";
            position: absolute;
            top: 50%;
            width: 40%;
            height: 1px;
            background: #e5e7eb;
        }
        .divider::before { left: 0; }
        .divider::after { right: 0; }
        .small-link {
            margin-top: 0.75rem;
            font-size: 0.8rem;
            color: #6b7280;
        }
        .full-width-btn button {
            width: 100% !important;
        }
        
        /* Admin Dashboard Cards */
        .metric-card {
            background-color: white;
            padding: 1rem;
            border-radius: 0.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            text-align: center;
        }
        .metric-label {
            font-size: 0.875rem;
            color: #6b7280;
        }
        .metric-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: #111827;
        }
        
        /* Upload Box */
        .upload-box {
            border: 2px dashed #e5e7eb;
            border-radius: 0.75rem;
            padding: 1.5rem;
            text-align: center;
            background-color: rgba(255,255,255,0.5);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

def app_header(logo_path: str = "img2.jpg"):
    cols = st.columns([1, 5])
    with cols[0]:
        try:
            if os.path.exists(logo_path):
                st.image(logo_path, width=100)
            else:
                st.write("🦷")
        except Exception:
            st.write("🦷")
    with cols[1]:
        st.markdown(
            "<h1 style='margin-top: 0;'>Smiles Dental Care</h1>",
            unsafe_allow_html=True,
        )
        st.caption("Clinic Assistant · Bookings · Reports · Chatbot (RAG-powered)")
