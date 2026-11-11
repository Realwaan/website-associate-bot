-- Scope settings and leaderboard entries by guild_id (0 = global / unscoped fallback).

ALTER TABLE settings ADD COLUMN IF NOT EXISTS guild_id BIGINT NOT NULL DEFAULT 0;
ALTER TABLE settings DROP CONSTRAINT IF EXISTS settings_pkey;
ALTER TABLE settings ADD PRIMARY KEY (guild_id, key);

ALTER TABLE leaderboard ADD COLUMN IF NOT EXISTS guild_id BIGINT NOT NULL DEFAULT 0;
ALTER TABLE leaderboard DROP CONSTRAINT IF EXISTS leaderboard_pkey;
ALTER TABLE leaderboard ADD PRIMARY KEY (guild_id, user_id);

CREATE INDEX IF NOT EXISTS idx_threads_guild_status ON threads (guild_id, status, created_at DESC);
