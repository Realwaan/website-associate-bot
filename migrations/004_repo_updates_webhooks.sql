-- Per-guild repo update configuration + idempotency + webhook replay protection.

CREATE TABLE IF NOT EXISTS repo_update_configs (
    guild_id BIGINT PRIMARY KEY,
    channel_id BIGINT NOT NULL,
    repo_url TEXT NOT NULL,
    repo_owner TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    branch TEXT NOT NULL DEFAULT 'main',
    feed_type TEXT NOT NULL DEFAULT 'both',
    post_limit INTEGER NOT NULL DEFAULT 10,
    mode TEXT NOT NULL DEFAULT 'polling',
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_repo_update_configs_enabled
    ON repo_update_configs (enabled, mode);

CREATE TABLE IF NOT EXISTS posted_repo_events (
    event_key TEXT NOT NULL,
    channel_id BIGINT NOT NULL,
    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (event_key, channel_id)
);

CREATE TABLE IF NOT EXISTS github_webhook_receipts (
    delivery_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
