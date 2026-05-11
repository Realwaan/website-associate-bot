-- Dead-letter queue support for webhook processing reliability.

CREATE TABLE IF NOT EXISTS webhook_dead_letters (
    id SERIAL PRIMARY KEY,
    delivery_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    error_text TEXT NOT NULL,
    retry_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_attempt_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_webhook_dead_letters_pending
    ON webhook_dead_letters (status, next_attempt_at);
