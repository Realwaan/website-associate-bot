ALTER TABLE threads ADD COLUMN IF NOT EXISTS external_task_id TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS threads_external_task_id_idx
    ON threads (external_task_id)
    WHERE external_task_id IS NOT NULL;
