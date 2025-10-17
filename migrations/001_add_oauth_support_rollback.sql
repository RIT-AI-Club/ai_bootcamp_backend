-- Migration Rollback: Remove OAuth Support
-- Date: 2025-10-16
-- Description: Rollback OAuth authentication support
--
-- WARNING: This will remove OAuth accounts and make password_hash required again
-- Only run this if you need to revert the OAuth implementation
--
-- This rollback:
-- 1. Removes oauth_accounts table and related objects
-- 2. Makes password_hash NOT NULL again (will fail if OAuth users exist)

-- ============================================================================
-- SAFETY CHECK: Verify no OAuth-only users exist
-- ============================================================================

DO $$
DECLARE
    oauth_user_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO oauth_user_count
    FROM users
    WHERE password_hash IS NULL;

    IF oauth_user_count > 0 THEN
        RAISE EXCEPTION 'Cannot rollback: % users exist with NULL password_hash (OAuth-only users). Please assign passwords or delete these users first.', oauth_user_count;
    ELSE
        RAISE NOTICE 'Safety check passed: No OAuth-only users found';
    END IF;
END $$;

-- ============================================================================
-- 1. Drop oauth_accounts table and related objects
-- ============================================================================

-- Drop trigger
DROP TRIGGER IF EXISTS update_oauth_accounts_updated_at ON oauth_accounts;

-- Drop indexes
DROP INDEX IF EXISTS idx_oauth_accounts_user_id;
DROP INDEX IF EXISTS idx_oauth_accounts_provider;
DROP INDEX IF EXISTS idx_oauth_accounts_provider_account;

-- Drop table
DROP TABLE IF EXISTS oauth_accounts CASCADE;

RAISE NOTICE '✓ Removed oauth_accounts table and related objects';

-- ============================================================================
-- 2. Make password_hash NOT NULL again
-- ============================================================================

-- This will fail if any users have NULL password_hash
ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL;

RAISE NOTICE '✓ password_hash column is now required (NOT NULL)';

-- ============================================================================
-- Rollback complete
-- ============================================================================

DO $$
BEGIN
    RAISE NOTICE '════════════════════════════════════════════════════════';
    RAISE NOTICE 'Rollback 001_add_oauth_support completed successfully';
    RAISE NOTICE '════════════════════════════════════════════════════════';
    RAISE NOTICE '';
    RAISE NOTICE 'Changes reverted:';
    RAISE NOTICE '  - users.password_hash is now NOT NULL (required)';
    RAISE NOTICE '  - oauth_accounts table removed';
    RAISE NOTICE '  - All OAuth-related indexes and triggers removed';
    RAISE NOTICE '';
    RAISE NOTICE 'Next steps:';
    RAISE NOTICE '  1. Remove OAuth code from backend';
    RAISE NOTICE '  2. Restart backend service';
    RAISE NOTICE '  3. Restore original frontend login forms';
    RAISE NOTICE '';
    RAISE NOTICE '════════════════════════════════════════════════════════';
END $$;
