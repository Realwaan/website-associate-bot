-- Durable idempotency and delivery records for the website <-> Discord bridge.
-- These records make retries safe across Render restarts and deployments.

ALTER TABLE threads ADD COLUMN IF NOT EXISTS guild_id BIGINT;

CREATE TABLE IF NOT EXISTS capstone_integration_deliveries (
    id BIGSERIAL PRIMARY KEY,
    idempotency_key TEXT NOT NULL UNIQUE,
    correlation_id TEXT NOT NULL,
    operation TEXT NOT NULL,
    external_task_id TEXT,
    request_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    response_json JSONB,
    response_status INTEGER,
    state TEXT NOT NULL DEFAULT 'processing'
        CHECK (state IN ('processing', 'succeeded', 'failed')),
    error_text TEXT,
    attempts INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_capstone_integration_task
    ON capstone_integration_deliveries (external_task_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_capstone_integration_state
    ON capstone_integration_deliveries (state, updated_at DESC);
