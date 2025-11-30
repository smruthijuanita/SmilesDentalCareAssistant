# 🦷 Smiles Dental Care - AI-Powered Booking Assistant

A comprehensive dental care management system built with Streamlit, featuring AI-powered chat assistance, appointment booking, and admin analytics dashboard.

## ✨ Features

### For Patients
- 🤖 **AI Chat Assistant** - Get instant answers to dental queries with RAG-powered context
- 📅 **Easy Booking** - Conversational appointment booking flow
- 📁 **Document Upload** - Share dental records and x-rays securely
- 🔐 **Secure Authentication** - Personal account with booking history

### For Admins
- 📊 **Comprehensive Dashboard** - 7 key metrics at a glance
- 👥 **Patient Management** - View all patients with booking statistics
- 🩺 **Doctor Management** - Manage doctors, specialities, and availability
- 📅 **Booking Management** - Advanced filters and status updates
- 📁 **Document Tracking** - Monitor uploaded patient documents
- 📈 **Analytics** - Visualize trends, performance, and utilization
- 💾 **CSV Exports** - Download data for all tables

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Supabase account (for database)
- Groq API key (for AI chat)
- Gmail account with App Password (for email notifications)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/smruthijuanita/smilesdentalcare.git
   cd smilesdentalcare
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your credentials:
   ```env
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASSWORD=your_gmail_app_password
   EMAIL_FROM_NAME=Clinic Assistant
   GROQ_API_KEY=your_groq_api_key
   DEBUG=False
   ```

5. **Setup Supabase database**
   - Go to your Supabase Dashboard
   - Navigate to SQL Editor
   - Run the SQL from `migrations/create_tables.sql`

6. **Run the application**
   ```bash
   streamlit run app.py
   ```

## 🔐 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | ✅ Yes |
| `SUPABASE_KEY` | Supabase anon/service key | ✅ Yes |
| `EMAIL_HOST` | SMTP server host | ✅ Yes |
| `EMAIL_PORT` | SMTP server port | ✅ Yes |
| `EMAIL_USER` | SMTP username (email) | ✅ Yes |
| `EMAIL_PASSWORD` | SMTP password/app password | ✅ Yes |
| `EMAIL_FROM_NAME` | Sender name for emails | No |
| `GROQ_API_KEY` | Groq API key for AI chat | ✅ Yes |
| `DEBUG` | Enable debug mode | No |

### Getting API Keys

**Supabase:**
1. Sign up at [supabase.com](https://supabase.com)
2. Create a new project
3. Go to Project Settings → API
4. Copy `URL` and `anon public` key

**Groq:**
1. Sign up at [groq.com](https://groq.com)
2. Go to API Keys section
3. Generate a new API key

**Gmail App Password:**
1. Enable 2-Factor Authentication on your Google account
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Generate an app password for "Mail"
4. Use this password in `EMAIL_PASSWORD`

## 📁 Project Structure

```
smilesdentalcare/
├── app.py                          # Main Streamlit application
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
├── .gitignore                      # Git ignore rules
├── migrations/
│   └── create_tables.sql          # Database schema
├── modules/
│   ├── admin_utils.py             # Admin helper functions
│   ├── booking_flow.py            # Booking workflow logic
│   ├── chat_engine.py             # AI chat integration
│   ├── db.py                      # Database abstraction layer
│   ├── email_utils.py             # Email notifications
│   ├── emergency_detector.py      # Emergency detection
│   ├── file_utils.py              # File upload handling
│   ├── rag_pipeline.py            # RAG with FAISS
│   ├── settings.py                # Configuration management
│   ├── supabase_client.py         # Supabase API wrapper
│   └── ui_components.py           # Reusable UI components
└── tests/
    └── test_core.py               # Unit tests
```

## 🌐 Deployment to Streamlit Cloud

1. **Push to GitHub** (already done!)

2. **Go to [share.streamlit.io](https://share.streamlit.io)**

3. **Deploy new app:**
   - Repository: `smruthijuanita/smilesdentalcare`
   - Branch: `main`
   - Main file: `app.py`

4. **Add secrets** in Streamlit Cloud settings:
   ```toml
   SUPABASE_URL = "your_supabase_url"
   SUPABASE_KEY = "your_supabase_key"
   EMAIL_HOST = "smtp.gmail.com"
   EMAIL_PORT = 587
   EMAIL_USER = "your_email@gmail.com"
   EMAIL_PASSWORD = "your_app_password"
   EMAIL_FROM_NAME = "Clinic Assistant"
   GROQ_API_KEY = "your_groq_api_key"
   DEBUG = false
   ```

5. **Deploy!** 🚀

## 👨‍💼 Admin Access

Default admin credentials (change these after first login):
- Email: `admin@smilesdentalcare.com`
- Password: (created during user registration with role='admin')

To create admin user, manually update the `role` field in Supabase:
```sql
UPDATE users SET role = 'admin' WHERE email = 'your_admin@email.com';
```

## 🛠️ Tech Stack

- **Frontend:** Streamlit
- **Database:** Supabase (PostgreSQL)
- **AI/ML:** 
  - Groq (LLM)
  - FAISS (Vector search)
  - Sentence Transformers (Embeddings)
- **Authentication:** Custom with Supabase
- **Email:** SMTP (Gmail)
- **Deployment:** Streamlit Cloud

## 📚 Documentation

- [Admin Dashboard Upgrade Guide](ADMIN_DASHBOARD_UPGRADE.md)
- [Security Fix Documentation](SECURITY_FIX.md)

## 🔒 Security

- All secrets managed via environment variables
- `.env` file never committed to git
- Passwords hashed in database
- Secure session management
- GitHub Push Protection enabled

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## 📄 License

This project is private and proprietary.

## 📧 Contact

For issues or questions, please open an issue on GitHub.

---

**Made with ❤️ for Smiles Dental Care**
