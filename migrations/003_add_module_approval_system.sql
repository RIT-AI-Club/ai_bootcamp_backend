-- Migration: Add instructor approval system for module completions
-- Date: 2025-10-16
-- Purpose: Allow admins to review and approve student module completions before they can progress

\c aibc_db;

-- Add approval fields to module_completions table
ALTER TABLE module_completions
ADD COLUMN IF NOT EXISTS approval_status VARCHAR(50) DEFAULT 'pending' CHECK (approval_status IN ('pending', 'approved', 'rejected')),
ADD COLUMN IF NOT EXISTS reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,
ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP WITH TIME ZONE,
ADD COLUMN IF NOT EXISTS review_comments TEXT;

-- Create index for pending approvals query
CREATE INDEX IF NOT EXISTS idx_module_completions_approval_status ON module_completions(approval_status);
CREATE INDEX IF NOT EXISTS idx_module_completions_pending_review ON module_completions(approval_status, completed_at) WHERE approval_status = 'pending';

-- Update existing completions to 'approved' (grandfathering existing progress)
UPDATE module_completions
SET approval_status = 'approved'
WHERE approval_status = 'pending' AND completed_at IS NOT NULL;

-- Add comment
COMMENT ON COLUMN module_completions.approval_status IS 'Instructor approval status: pending (waiting review), approved (can progress), rejected (needs rework)';
COMMENT ON COLUMN module_completions.reviewed_by IS 'Instructor/admin who reviewed the module completion';
COMMENT ON COLUMN module_completions.reviewed_at IS 'Timestamp when the review was completed';
COMMENT ON COLUMN module_completions.review_comments IS 'Instructor feedback on the module completion';

-- Create view for pending module reviews
CREATE OR REPLACE VIEW pending_module_reviews AS
SELECT
    mc.id,
    mc.user_id,
    u.email as user_email,
    u.full_name as user_name,
    mc.pathway_id,
    p.title as pathway_title,
    mc.module_id,
    m.title as module_title,
    mc.completed_at,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - mc.completed_at))/3600 as hours_waiting,
    -- Count of completed resources
    (SELECT COUNT(*) FROM resource_completions rc
     WHERE rc.user_id = mc.user_id
     AND rc.module_id = mc.module_id
     AND rc.status IN ('completed', 'submitted', 'reviewed')) as completed_resources,
    -- Count of total resources
    (SELECT COUNT(*) FROM resources r WHERE r.module_id = mc.module_id) as total_resources
FROM module_completions mc
JOIN users u ON mc.user_id = u.id
JOIN pathways p ON mc.pathway_id = p.id
JOIN modules m ON mc.module_id = m.id
WHERE mc.approval_status = 'pending'
  AND mc.completed_at IS NOT NULL
ORDER BY mc.completed_at ASC;

-- Verification
SELECT 'Module Completions Schema:' as info;
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'module_completions'
  AND column_name IN ('approval_status', 'reviewed_by', 'reviewed_at', 'review_comments')
ORDER BY ordinal_position;

SELECT 'Pending Reviews Count:' as info;
SELECT COUNT(*) as pending_count FROM module_completions WHERE approval_status = 'pending' AND completed_at IS NOT NULL;
