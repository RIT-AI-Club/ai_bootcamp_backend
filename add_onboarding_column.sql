-- Migration: Add onboarding_completed column to users table
-- This script is idempotent and can be run multiple times safely

\c aibc_db;

-- Add onboarding_completed column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users'
        AND column_name = 'onboarding_completed'
    ) THEN
        ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT FALSE;
        RAISE NOTICE 'Column onboarding_completed added to users table';
    ELSE
        RAISE NOTICE 'Column onboarding_completed already exists in users table';
    END IF;
END $$;

-- Update existing users to have onboarding_completed = false
-- (This is safe as DEFAULT FALSE will handle new users)
UPDATE users SET onboarding_completed = FALSE WHERE onboarding_completed IS NULL;

RAISE NOTICE 'Migration completed successfully';
