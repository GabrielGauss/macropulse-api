-- Add attempt counter to email_verifications to prevent OTP brute-force.
-- After 5 wrong guesses the row is exhausted (used = TRUE).
ALTER TABLE email_verifications
    ADD COLUMN IF NOT EXISTS attempts INT NOT NULL DEFAULT 0;
