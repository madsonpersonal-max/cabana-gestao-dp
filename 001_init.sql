CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  username TEXT UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('DP','GERENCIA','FINANCEIRO','ADMIN','FISCAL')),
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS employees (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  code TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  sector TEXT,
  cargo TEXT,
  status TEXT NOT NULL DEFAULT 'Ativo',
  admission_date DATE,
  dismissal_date DATE,
  dismissal_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS employee_history (
  id BIGSERIAL PRIMARY KEY,
  employee_id UUID NOT NULL REFERENCES employees(id),
  event_type TEXT NOT NULL,
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS vacations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id),
  accrual_period TEXT,
  concession_period TEXT,
  start_date DATE,
  end_date DATE,
  status TEXT NOT NULL DEFAULT 'Programada',
  payment_evidence TEXT,
  evidence_file TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS absences (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id),
  absence_type TEXT NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE,
  status TEXT NOT NULL DEFAULT 'Em andamento',
  evidence_file TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS aso (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID NOT NULL REFERENCES employees(id),
  exam_type TEXT NOT NULL,
  exam_date DATE NOT NULL,
  next_due DATE NOT NULL,
  status TEXT NOT NULL,
  evidence_file TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  employee_id UUID REFERENCES employees(id),
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  document_number TEXT,
  issuing_body TEXT,
  issue_date DATE,
  expiration_date DATE,
  responsible TEXT,
  substitute TEXT,
  status TEXT NOT NULL,
  file_path TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS monthly_closures (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  competence TEXT UNIQUE NOT NULL,
  status TEXT NOT NULL DEFAULT 'Em andamento',
  version INTEGER NOT NULL DEFAULT 1,
  dp_percent INTEGER NOT NULL DEFAULT 0,
  finance_percent INTEGER NOT NULL DEFAULT 0,
  closed_at TIMESTAMPTZ,
  closed_by UUID REFERENCES users(id),
  reopen_reason TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID REFERENCES users(id),
  action TEXT NOT NULL,
  entity TEXT NOT NULL,
  record_id TEXT,
  details JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_employees_status ON employees(status);
CREATE INDEX IF NOT EXISTS idx_employees_sector ON employees(sector);
CREATE INDEX IF NOT EXISTS idx_employee_history_employee ON employee_history(employee_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_vacations_employee ON vacations(employee_id, start_date DESC);
CREATE INDEX IF NOT EXISTS idx_absences_employee ON absences(employee_id, start_date DESC);
CREATE INDEX IF NOT EXISTS idx_aso_employee ON aso(employee_id, exam_date DESC);
CREATE INDEX IF NOT EXISTS idx_documents_expiration ON documents(expiration_date);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at DESC);
