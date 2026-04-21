-- Normalize reminders channel setting so "unset" is represented by key absence.
-- Remove blank or whitespace-only reminders_channel_id values.
DELETE FROM settings
WHERE key = 'reminders_channel_id'
  AND TRIM(value) = '';
