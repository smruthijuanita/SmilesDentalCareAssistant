-- Supabase migration: create Customer, Doctor, Booking tables provided by user

-- Customer table
CREATE TABLE IF NOT EXISTS Customer (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    event VARCHAR(100),
    phone_number VARCHAR(20)
);

-- Doctor table (legacy - keeping for compatibility)
CREATE TABLE IF NOT EXISTS Doctor (
    doctor_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100)
);

-- Booking table linking to Customer and Doctor (legacy)
CREATE TABLE IF NOT EXISTS Booking (
    booking_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES Customer(customer_id),
    doctor_id INT REFERENCES Doctor(doctor_id),
    date DATE,
    timestamp TIMESTAMP,
    status VARCHAR(50)
);

-- Additional tables for the Streamlit app: users, bookings, uploads
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200),
    email VARCHAR(255) UNIQUE,
    password_hash TEXT,
    role VARCHAR(50) DEFAULT 'user',
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Doctors table for admin dashboard
CREATE TABLE IF NOT EXISTS doctors (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    email VARCHAR(255) UNIQUE,
    speciality VARCHAR(100),
    phone VARCHAR(20),
    status VARCHAR(20) DEFAULT 'available',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    doctor_id INT REFERENCES doctors(id),
    appt_date DATE,
    appt_time TEXT,
    reason TEXT,
    status VARCHAR(50) DEFAULT 'Pending',
    booking_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS uploads (
    id SERIAL PRIMARY KEY,
    user_id INT REFERENCES users(id),
    file_path TEXT,
    file_type VARCHAR(50),
    original_name TEXT,
    uploaded_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id);
CREATE INDEX IF NOT EXISTS idx_bookings_doctor_id ON bookings(doctor_id);
CREATE INDEX IF NOT EXISTS idx_bookings_appt_date ON bookings(appt_date);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_uploads_user_id ON uploads(user_id);
CREATE INDEX IF NOT EXISTS idx_doctors_email ON doctors(email);

-- Insert sample doctors if none exist
INSERT INTO doctors (name, email, speciality, phone, status)
SELECT 'Dr. Sarah Johnson', 'dr.sarah@smilesdentalcare.com', 'General Dentistry', '+1-555-0101', 'available'
WHERE NOT EXISTS (SELECT 1 FROM doctors WHERE email = 'dr.sarah@smilesdentalcare.com');

INSERT INTO doctors (name, email, speciality, phone, status)
SELECT 'Dr. Michael Chen', 'dr.chen@smilesdentalcare.com', 'Orthodontics', '+1-555-0102', 'available'
WHERE NOT EXISTS (SELECT 1 FROM doctors WHERE email = 'dr.chen@smilesdentalcare.com');

INSERT INTO doctors (name, email, speciality, phone, status)
SELECT 'Dr. Emily Rodriguez', 'dr.rodriguez@smilesdentalcare.com', 'Pediatric Dentistry', '+1-555-0103', 'available'
WHERE NOT EXISTS (SELECT 1 FROM doctors WHERE email = 'dr.rodriguez@smilesdentalcare.com');
