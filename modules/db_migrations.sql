-- Enable UUID extension
create extension if not exists "uuid-ossp";

-- Users table
create table if not exists public.users (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    email text unique not null,
    password_hash text not null,
    role text default 'user',
    phone text,
    created_at timestamptz default now()
);

-- Doctors table
create table if not exists public.doctors (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    email text,
    speciality text,
    phone text,
    status text default 'available',
    created_at timestamptz default now()
);

-- Bookings table
create table if not exists public.bookings (
    id bigserial primary key,
    user_id uuid references public.users(id),
    doctor_id uuid references public.doctors(id),
    appt_date date not null,
    appt_time text not null,
    reason text,
    status text default 'Pending',
    booking_type text,
    created_at timestamptz default now()
);

-- Uploads table
create table if not exists public.uploads (
    id bigserial primary key,
    user_id uuid references public.users(id),
    file_path text not null,
    original_name text,
    file_type text,
    uploaded_at timestamptz default now()
);

-- Indexes
create index if not exists idx_bookings_user_id on public.bookings(user_id);
create index if not exists idx_bookings_doctor_id on public.bookings(doctor_id);
create index if not exists idx_bookings_appt_date on public.bookings(appt_date);
create index if not exists idx_uploads_user_id on public.uploads(user_id);

-- Default Admin User (password: admin123)
-- Hash: 240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9
INSERT INTO public.users (name, email, password_hash, role)
VALUES ('Admin', 'admin@example.com', '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9', 'admin')
ON CONFLICT (email) DO NOTHING;

-- Default Doctor (Dr. Smith)
INSERT INTO public.doctors (name, email, speciality, status)
VALUES ('Dr. Smith', 'smith@example.com', 'General Dentist', 'available')
ON CONFLICT DO NOTHING;
