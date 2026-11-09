-- Reserve an import before external effects. An uncertain create must be reconciled,
-- never blindly repeated after a crash.
ALTER TABLE loaded_tickets DROP CONSTRAINT IF EXISTS loaded_tickets_ticket_filename_folder_key;
CREATE UNIQUE INDEX IF NOT EXISTS idx_loaded_ticket_channel
    ON loaded_tickets (ticket_filename, folder, channel_id);

CREATE TABLE IF NOT EXISTS ticket_import_jobs (
    channel_id BIGINT NOT NULL,
    folder TEXT NOT NULL,
    filename TEXT NOT NULL,
    thread_id BIGINT,
    state TEXT NOT NULL DEFAULT 'pending' CHECK (state IN ('pending', 'complete')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (channel_id, folder, filename)
);
