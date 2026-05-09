-- Persist command telemetry and admin/audit events.

CREATE TABLE IF NOT EXISTS command_metrics (
    id SERIAL PRIMARY KEY,
    command_name TEXT NOT NULL,
    actor_id BIGINT,
    success BOOLEAN NOT NULL,
    duration_ms INTEGER NOT NULL,
    error_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_command_metrics_name_created
    ON command_metrics (command_name, created_at DESC);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    actor_id BIGINT,
    actor_name TEXT,
    details JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_event_created
    ON audit_logs (event_type, created_at DESC);
