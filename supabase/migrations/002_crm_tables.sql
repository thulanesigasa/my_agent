-- ====================================================================
-- Migration: 002_crm_tables.sql
-- Description: Structured CRM tables for T.S Industries clients and project sales pipeline
-- ====================================================================

-- 1. Enable UUID Extension if not already active
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Create Clients Table
CREATE TABLE IF NOT EXISTS public.clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT DEFAULT '',
    company TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create Projects Table
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES public.clients(id) ON DELETE CASCADE,
    status TEXT NOT NULL DEFAULT 'Lead' CHECK (status IN ('Lead', 'Quoted', 'In Progress', 'Completed', 'Lost')),
    quoted_price NUMERIC(12, 2) DEFAULT 0.00,
    scope_summary TEXT DEFAULT '',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Create Performance Indexes
CREATE INDEX IF NOT EXISTS idx_clients_email ON public.clients(email);
CREATE INDEX IF NOT EXISTS idx_projects_client_id ON public.projects(client_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON public.projects(status);

-- 5. Row Level Security (RLS) Policies
ALTER TABLE public.clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;

-- Allow service_role (backend API agent) full access to clients
CREATE POLICY "Service Role Full Access on Clients"
ON public.clients
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Allow authenticated admin full access to clients
CREATE POLICY "Authenticated Admin Access on Clients"
ON public.clients
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- Allow service_role (backend API agent) full access to projects
CREATE POLICY "Service Role Full Access on Projects"
ON public.projects
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Allow authenticated admin full access to projects
CREATE POLICY "Authenticated Admin Access on Projects"
ON public.projects
FOR ALL
TO authenticated
USING (true)
WITH CHECK (true);

-- 6. Automatically Update Timestamp Trigger
CREATE OR REPLACE FUNCTION update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_clients_timestamp
BEFORE UPDATE ON public.clients
FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();

CREATE TRIGGER update_projects_timestamp
BEFORE UPDATE ON public.projects
FOR EACH ROW EXECUTE FUNCTION update_timestamp_column();
