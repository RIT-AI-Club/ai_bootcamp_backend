-- Migration: Add OAuth Support
-- Date: 2025-10-16
-- Description: Updates schema to support Google OAuth authentication
--
-- This migration:
-- 1. Makes password_hash nullable for OAuth users
-- 2. Ensures oauth_accounts table exists with proper structure
-- 3. Is idempotent (safe to run multiple times)

-- ============================================================================
-- 1. Make password_hash nullable for OAuth users
-- ============================================================================

-- Check if column constraint needs to be updated
DO $$
BEGIN
    -- Alter the password_hash column to be nullable
    ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
    RAISE NOTICE 'Password hash column updated to allow NULL values for OAuth users';
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'Password hash column already nullable or error occurred: %', SQLERRM;
END $$;

-- ============================================================================
-- 2. Ensure oauth_accounts table exists
-- ============================================================================

CREATE TABLE IF NOT EXISTS oauth_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    provider_account_id VARCHAR(255) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(provider, provider_account_id)
);

-- ============================================================================
-- 3. Create indexes for oauth_accounts (if they don't exist)
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_oauth_accounts_user_id ON oauth_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_oauth_accounts_provider ON oauth_accounts(provider);
CREATE INDEX IF NOT EXISTS idx_oauth_accounts_provider_account ON oauth_accounts(provider, provider_account_id);

-- ============================================================================
-- 4. Create updated_at trigger for oauth_accounts
-- ============================================================================

-- Function already exists from init-complete.sql, just create trigger
DO $$
BEGIN
    -- Create trigger if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'update_oauth_accounts_updated_at'
    ) THEN
        CREATE TRIGGER update_oauth_accounts_updated_at
        BEFORE UPDATE ON oauth_accounts
        FOR EACH ROW
        EXECUTE FUNCTION update_updated_at_column();

        RAISE NOTICE 'Created trigger for oauth_accounts updated_at';
    ELSE
        RAISE NOTICE 'Trigger for oauth_accounts updated_at already exists';
    END IF;
END $$;

-- ============================================================================
-- 5. Verification queries
-- ============================================================================

-- Verify password_hash is nullable
DO $$
DECLARE
    v_is_nullable TEXT;
BEGIN
    SELECT c.is_nullable INTO v_is_nullable
    FROM information_schema.columns c
    WHERE c.table_name = 'users'
    AND c.column_name = 'password_hash';

    IF v_is_nullable = 'YES' THEN
        RAISE NOTICE '✓ password_hash column is nullable';
    ELSE
        RAISE WARNING '✗ password_hash column is still NOT NULL';
    END IF;
END $$;

-- Verify oauth_accounts table exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'oauth_accounts'
    ) THEN
        RAISE NOTICE '✓ oauth_accounts table exists';
    ELSE
        RAISE WARNING '✗ oauth_accounts table does not exist';
    END IF;
END $$;

-- Count existing OAuth accounts
DO $$
DECLARE
    oauth_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO oauth_count FROM oauth_accounts;
    RAISE NOTICE '✓ oauth_accounts table has % records', oauth_count;
END $$;

-- ============================================================================
-- Migration complete
-- ============================================================================

-- Display summary
DO $$
BEGIN
    RAISE NOTICE '════════════════════════════════════════════════════════';
    RAISE NOTICE 'Migration 001_add_oauth_support.sql completed successfully';
    RAISE NOTICE '════════════════════════════════════════════════════════';
    RAISE NOTICE '';
    RAISE NOTICE 'Changes applied:';
    RAISE NOTICE '  - users.password_hash is now nullable';
    RAISE NOTICE '  - oauth_accounts table created/verified';
    RAISE NOTICE '  - Indexes created for optimal performance';
    RAISE NOTICE '  - Triggers configured for timestamp updates';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Configure Google OAuth credentials in .env';
    RAISE NOTICE '  2. Restart backend service';
    RAISE NOTICE '  3. Test OAuth flow at /landing';
    RAISE NOTICE '';
    RAISE NOTICE '════════════════════════════════════════════════════════';
END $$;
