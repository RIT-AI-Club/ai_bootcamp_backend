-- Migration: Add Email Notification System
-- Purpose: Track email notifications sent to users and admins
-- Created: 2025-01-19

\c aibc_db;

-- ============================================================================
-- EMAIL LOGS TABLE
-- ============================================================================
-- Track all sent emails for auditing, debugging, and retry logic
CREATE TABLE IF NOT EXISTS email_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Recipient information
    recipient_email VARCHAR(255) NOT NULL,
    recipient_user_id UUID REFERENCES users(id) ON DELETE SET NULL,

    -- Email metadata
    email_type VARCHAR(100) NOT NULL,  -- 'module_approved', 'module_rejected', 'module_submitted', 'resource_reviewed'
    subject VARCHAR(500) NOT NULL,
    template_name VARCHAR(200),

    -- Email status
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'sent', 'failed', 'bounced')),
    sent_at TIMESTAMP WITH TIME ZONE,
    failed_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,

    -- Context data (JSON for flexibility)
    context_data JSONB,

    -- Reference to related entities
    module_id VARCHAR(100) REFERENCES modules(id) ON DELETE SET NULL,
    pathway_id VARCHAR(100) REFERENCES pathways(id) ON DELETE SET NULL,
    resource_submission_id UUID REFERENCES resource_submissions(id) ON DELETE SET NULL,
    module_completion_id UUID REFERENCES module_completions(id) ON DELETE SET NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================
CREATE INDEX idx_email_logs_recipient ON email_logs(recipient_email);
CREATE INDEX idx_email_logs_status ON email_logs(status);
CREATE INDEX idx_email_logs_type ON email_logs(email_type);
CREATE INDEX idx_email_logs_created_at ON email_logs(created_at DESC);
CREATE INDEX idx_email_logs_user_id ON email_logs(recipient_user_id);
CREATE INDEX idx_email_logs_module_id ON email_logs(module_id);
CREATE INDEX idx_email_logs_retry ON email_logs(status, retry_count) WHERE status = 'failed';

-- ============================================================================
-- TRIGGERS
-- ============================================================================
-- Auto-update updated_at timestamp
CREATE TRIGGER update_email_logs_updated_at BEFORE UPDATE ON email_logs
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- USER EMAIL PREFERENCES (Optional - for future enhancement)
-- ============================================================================
-- Add columns to users table for email preferences
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_notifications_enabled BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_on_module_approval BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_on_module_rejection BOOLEAN DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_on_resource_review BOOLEAN DEFAULT TRUE;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
