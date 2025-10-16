-- Migration: Add Resource-Level Progress Tracking and File Uploads
-- Purpose: Track individual resource completions and file submissions for exercises/projects
-- Created: 2025-10-16

\c aibc_db;

-- ============================================================================
-- 1. RESOURCES TABLE
-- ============================================================================
-- Stores all pathway resources (videos, articles, exercises, projects)
-- This normalizes the resources from JSON into the database
CREATE TABLE IF NOT EXISTS resources (
    id VARCHAR(200) PRIMARY KEY,  -- Format: {module_id}_{resource_index} or custom ID
    module_id VARCHAR(100) NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    pathway_id VARCHAR(100) NOT NULL REFERENCES pathways(id) ON DELETE CASCADE,

    -- Resource metadata
    type VARCHAR(50) NOT NULL CHECK (type IN ('video', 'article', 'exercise', 'project', 'quiz')),
    title VARCHAR(500) NOT NULL,
    description TEXT,

    -- Ordering and duration
    order_index INTEGER NOT NULL,  -- Order within the module
    duration_minutes INTEGER,  -- Optional duration

    -- File upload configuration
    requires_upload BOOLEAN DEFAULT FALSE,  -- Does this resource require file submission?
    accepted_file_types TEXT[],  -- Array of accepted MIME types: ['image/*', 'application/pdf', 'text/*']
    max_file_size_mb INTEGER DEFAULT 50,  -- Max file size in MB (global max: 50 MB)
    allow_resubmission BOOLEAN DEFAULT TRUE,  -- Allow resubmission after rejection

    -- External links
    url TEXT,  -- Link to video, article, Colab notebook, etc.

    -- Metadata
    metadata JSONB,  -- Additional flexible data (quiz questions, exercise instructions, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Ensure unique ordering within a module
    UNIQUE(module_id, order_index)
);

-- ============================================================================
-- 2. RESOURCE COMPLETIONS TABLE
-- ============================================================================
-- Tracks user progress on individual resources (watched video, read article, completed exercise)
CREATE TABLE IF NOT EXISTS resource_completions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resource_id VARCHAR(200) NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    module_id VARCHAR(100) NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    pathway_id VARCHAR(100) NOT NULL REFERENCES pathways(id) ON DELETE CASCADE,

    -- Completion status
    status VARCHAR(50) DEFAULT 'not_started' CHECK (status IN ('not_started', 'in_progress', 'completed', 'submitted', 'reviewed')),

    -- Progress tracking
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    time_spent_minutes INTEGER DEFAULT 0,

    -- Timestamps
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Submission tracking (for exercises/projects)
    submission_required BOOLEAN DEFAULT FALSE,
    submission_count INTEGER DEFAULT 0,  -- Number of files submitted

    -- Metadata
    notes TEXT,  -- User notes on this resource
    metadata JSONB,  -- Flexible data (quiz answers, exercise results, etc.)

    -- Ensure one completion record per user per resource
    UNIQUE(user_id, resource_id)
);

-- ============================================================================
-- 3. RESOURCE SUBMISSIONS TABLE
-- ============================================================================
-- Tracks file uploads to Google Cloud Storage for exercises and projects
CREATE TABLE IF NOT EXISTS resource_submissions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resource_id VARCHAR(200) NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    resource_completion_id UUID NOT NULL REFERENCES resource_completions(id) ON DELETE CASCADE,

    -- File metadata
    file_name VARCHAR(500) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    file_type VARCHAR(100) NOT NULL,  -- MIME type

    -- Google Cloud Storage details
    gcs_bucket VARCHAR(255) NOT NULL,  -- GCS bucket name
    gcs_path TEXT NOT NULL,  -- Full path in GCS: pathways/{pathway_id}/users/{user_id}/resources/{resource_id}/{filename}
    gcs_url TEXT NOT NULL,  -- Signed URL or public URL

    -- Submission metadata
    submission_status VARCHAR(50) DEFAULT 'uploaded' CHECK (submission_status IN ('uploading', 'uploaded', 'processing', 'approved', 'rejected', 'failed')),
    upload_ip TEXT,  -- IP address of uploader

    -- Review and grading
    reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL,  -- Instructor who reviewed
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_comments TEXT,
    grade VARCHAR(10) CHECK (grade IN ('pass', 'fail', NULL)),  -- Simple pass/fail grading

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,  -- Soft delete

    -- Metadata
    metadata JSONB  -- Additional flexible data
);

-- ============================================================================
-- 4. INDEXES FOR PERFORMANCE
-- ============================================================================

-- Resources indexes
CREATE INDEX idx_resources_module_id ON resources(module_id);
CREATE INDEX idx_resources_pathway_id ON resources(pathway_id);
CREATE INDEX idx_resources_type ON resources(type);
CREATE INDEX idx_resources_module_order ON resources(module_id, order_index);
CREATE INDEX idx_resources_requires_upload ON resources(requires_upload) WHERE requires_upload = TRUE;

-- Resource completions indexes
CREATE INDEX idx_resource_completions_user_id ON resource_completions(user_id);
CREATE INDEX idx_resource_completions_resource_id ON resource_completions(resource_id);
CREATE INDEX idx_resource_completions_module_id ON resource_completions(module_id);
CREATE INDEX idx_resource_completions_pathway_id ON resource_completions(pathway_id);
CREATE INDEX idx_resource_completions_status ON resource_completions(status);
CREATE INDEX idx_resource_completions_completed_at ON resource_completions(completed_at);

-- Composite indexes for common queries
CREATE INDEX idx_resource_completions_user_pathway ON resource_completions(user_id, pathway_id, status);
CREATE INDEX idx_resource_completions_user_module ON resource_completions(user_id, module_id, status);

-- Resource submissions indexes
CREATE INDEX idx_resource_submissions_user_id ON resource_submissions(user_id);
CREATE INDEX idx_resource_submissions_resource_id ON resource_submissions(resource_id);
CREATE INDEX idx_resource_submissions_completion_id ON resource_submissions(resource_completion_id);
CREATE INDEX idx_resource_submissions_status ON resource_submissions(submission_status);
CREATE INDEX idx_resource_submissions_created_at ON resource_submissions(created_at);
CREATE INDEX idx_resource_submissions_gcs_path ON resource_submissions(gcs_path);

-- Composite indexes
CREATE INDEX idx_resource_submissions_user_resource ON resource_submissions(user_id, resource_id, created_at DESC);
CREATE INDEX idx_resource_submissions_review ON resource_submissions(submission_status, reviewed_at) WHERE reviewed_at IS NULL;

-- ============================================================================
-- 5. TRIGGERS
-- ============================================================================

-- Auto-update updated_at timestamp for resources
CREATE TRIGGER update_resources_updated_at BEFORE UPDATE ON resources
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Auto-update updated_at timestamp for resource_submissions
CREATE TRIGGER update_resource_submissions_updated_at BEFORE UPDATE ON resource_submissions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 6. FUNCTIONS FOR PROGRESS CALCULATION
-- ============================================================================

-- Function to calculate module completion percentage based on resources
CREATE OR REPLACE FUNCTION calculate_module_progress(p_user_id UUID, p_module_id VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    total_resources INTEGER;
    completed_resources INTEGER;
    progress_pct INTEGER;
BEGIN
    -- Count total resources in module
    SELECT COUNT(*) INTO total_resources
    FROM resources
    WHERE module_id = p_module_id;

    -- Return 0 if no resources
    IF total_resources = 0 THEN
        RETURN 0;
    END IF;

    -- Count completed resources
    SELECT COUNT(*) INTO completed_resources
    FROM resource_completions
    WHERE user_id = p_user_id
      AND module_id = p_module_id
      AND status IN ('completed', 'submitted', 'reviewed');

    -- Calculate percentage
    progress_pct := (completed_resources * 100) / total_resources;

    RETURN progress_pct;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate pathway completion percentage based on modules
CREATE OR REPLACE FUNCTION calculate_pathway_progress(p_user_id UUID, p_pathway_id VARCHAR)
RETURNS INTEGER AS $$
DECLARE
    total_modules INTEGER;
    completed_modules INTEGER;
    progress_pct INTEGER;
BEGIN
    -- Count total modules in pathway
    SELECT COUNT(*) INTO total_modules
    FROM modules
    WHERE pathway_id = p_pathway_id;

    -- Return 0 if no modules
    IF total_modules = 0 THEN
        RETURN 0;
    END IF;

    -- Count completed modules (where all resources are completed)
    SELECT COUNT(DISTINCT m.id) INTO completed_modules
    FROM modules m
    WHERE m.pathway_id = p_pathway_id
      AND NOT EXISTS (
          SELECT 1 FROM resources r
          WHERE r.module_id = m.id
            AND NOT EXISTS (
                SELECT 1 FROM resource_completions rc
                WHERE rc.user_id = p_user_id
                  AND rc.resource_id = r.id
                  AND rc.status IN ('completed', 'submitted', 'reviewed')
            )
      );

    -- Calculate percentage
    progress_pct := (completed_modules * 100) / total_modules;

    RETURN progress_pct;
END;
$$ LANGUAGE plpgsql;

-- Function to auto-update module_completions when all resources completed
CREATE OR REPLACE FUNCTION update_module_completion_on_resource_complete()
RETURNS TRIGGER AS $$
DECLARE
    module_progress INTEGER;
BEGIN
    -- Only proceed if status is completed/submitted/reviewed
    IF NEW.status IN ('completed', 'submitted', 'reviewed') THEN
        -- Calculate module progress
        module_progress := calculate_module_progress(NEW.user_id, NEW.module_id);

        -- If module is 100% complete, insert/update module_completions
        IF module_progress = 100 THEN
            INSERT INTO module_completions (user_id, pathway_id, module_id, completed_at)
            VALUES (NEW.user_id, NEW.pathway_id, NEW.module_id, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, module_id) DO NOTHING;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-complete modules when all resources done
CREATE TRIGGER trigger_auto_complete_module
    AFTER INSERT OR UPDATE ON resource_completions
    FOR EACH ROW EXECUTE FUNCTION update_module_completion_on_resource_complete();

-- Function to auto-update user_progress when modules completed
CREATE OR REPLACE FUNCTION update_pathway_progress_on_module_complete()
RETURNS TRIGGER AS $$
DECLARE
    pathway_progress INTEGER;
    total_time INTEGER;
BEGIN
    -- Calculate pathway progress
    pathway_progress := calculate_pathway_progress(NEW.user_id, NEW.pathway_id);

    -- Calculate total time spent
    SELECT COALESCE(SUM(time_spent_minutes), 0) INTO total_time
    FROM resource_completions
    WHERE user_id = NEW.user_id AND pathway_id = NEW.pathway_id;

    -- Update or insert user_progress
    INSERT INTO user_progress (
        user_id,
        pathway_id,
        current_module_id,
        progress_percentage,
        completed_modules,
        total_time_spent_minutes,
        last_accessed_at,
        completed_at
    )
    VALUES (
        NEW.user_id,
        NEW.pathway_id,
        NEW.module_id,
        pathway_progress,
        (SELECT COUNT(*) FROM module_completions WHERE user_id = NEW.user_id AND pathway_id = NEW.pathway_id),
        total_time,
        CURRENT_TIMESTAMP,
        CASE WHEN pathway_progress = 100 THEN CURRENT_TIMESTAMP ELSE NULL END
    )
    ON CONFLICT (user_id, pathway_id) DO UPDATE SET
        current_module_id = EXCLUDED.current_module_id,
        progress_percentage = EXCLUDED.progress_percentage,
        completed_modules = EXCLUDED.completed_modules,
        total_time_spent_minutes = EXCLUDED.total_time_spent_minutes,
        last_accessed_at = EXCLUDED.last_accessed_at,
        completed_at = EXCLUDED.completed_at;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update pathway progress
CREATE TRIGGER trigger_auto_update_pathway_progress
    AFTER INSERT OR UPDATE ON module_completions
    FOR EACH ROW EXECUTE FUNCTION update_pathway_progress_on_module_complete();

-- Function to increment submission_count when file uploaded
CREATE OR REPLACE FUNCTION increment_submission_count()
RETURNS TRIGGER AS $$
BEGIN
    -- Only increment on successful uploads
    IF NEW.submission_status = 'uploaded' THEN
        UPDATE resource_completions
        SET submission_count = submission_count + 1,
            status = 'submitted'
        WHERE id = NEW.resource_completion_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-increment submission count
CREATE TRIGGER trigger_increment_submission_count
    AFTER INSERT ON resource_submissions
    FOR EACH ROW EXECUTE FUNCTION increment_submission_count();

-- ============================================================================
-- 7. VIEWS FOR COMMON QUERIES
-- ============================================================================

-- View: User resource progress summary
CREATE OR REPLACE VIEW user_resource_progress_summary AS
SELECT
    rc.user_id,
    rc.pathway_id,
    rc.module_id,
    COUNT(*) as total_resources,
    SUM(CASE WHEN rc.status IN ('completed', 'submitted', 'reviewed') THEN 1 ELSE 0 END) as completed_resources,
    SUM(CASE WHEN rc.submission_required THEN 1 ELSE 0 END) as resources_requiring_submission,
    SUM(rc.submission_count) as total_submissions,
    SUM(rc.time_spent_minutes) as total_time_spent
FROM resource_completions rc
GROUP BY rc.user_id, rc.pathway_id, rc.module_id;

-- View: Pending submissions for review
CREATE OR REPLACE VIEW pending_submissions AS
SELECT
    rs.id,
    rs.user_id,
    u.email as user_email,
    u.full_name as user_name,
    rs.resource_id,
    r.title as resource_title,
    r.type as resource_type,
    rs.file_name,
    rs.gcs_url,
    rs.created_at,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - rs.created_at))/3600 as hours_waiting
FROM resource_submissions rs
JOIN users u ON rs.user_id = u.id
JOIN resources r ON rs.resource_id = r.id
WHERE rs.submission_status = 'uploaded'
  AND rs.reviewed_at IS NULL
  AND rs.deleted_at IS NULL
ORDER BY rs.created_at ASC;

-- ============================================================================
-- 8. SAMPLE DATA (for testing - image-generation pathway)
-- ============================================================================

-- Insert resources for image-generation pathway module 1 (foundations-image-gen)
INSERT INTO resources (id, module_id, pathway_id, type, title, order_index, duration_minutes, requires_upload, url) VALUES
('foundations-image-gen-r1', 'foundations-image-gen', 'image-generation', 'video', 'What is AI Image Generation + Model Types', 1, 40, FALSE, NULL),
('foundations-image-gen-r2', 'foundations-image-gen', 'image-generation', 'article', 'Overview of Stable Diffusion, Imagen, DALL·E, Gemini (PDF)', 2, NULL, FALSE, NULL),
('foundations-image-gen-r3', 'foundations-image-gen', 'image-generation', 'exercise', 'Simple Stable Diffusion prompt generation (Colab)', 3, 45, TRUE, NULL),
('foundations-image-gen-r4', 'foundations-image-gen', 'image-generation', 'quiz', 'Quiz: 8 MCQ on model types and use-cases', 4, NULL, FALSE, NULL),
('foundations-image-gen-r5', 'foundations-image-gen', 'image-generation', 'project', 'Generate 3 mood-board images for fictional product', 5, NULL, TRUE, NULL)
ON CONFLICT (id) DO NOTHING;

-- Set file upload requirements for exercises and projects
UPDATE resources SET
    requires_upload = TRUE,
    accepted_file_types = ARRAY['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'application/pdf'],
    max_file_size_mb = 25
WHERE type IN ('exercise', 'project') AND pathway_id = 'image-generation';

-- Insert resources for prompt-engineering pathway module 1 (prompting-foundations)
INSERT INTO resources (id, module_id, pathway_id, type, title, order_index, duration_minutes, requires_upload, url) VALUES
('prompting-foundations-r1', 'prompting-foundations', 'prompt-engineering', 'video', 'Why Prompts Matter — Talking to AI', 1, 35, FALSE, NULL),
('prompting-foundations-r2', 'prompting-foundations', 'prompt-engineering', 'article', 'Good vs Bad Prompts Examples (PDF)', 2, NULL, FALSE, NULL),
('prompting-foundations-r3', 'prompting-foundations', 'prompt-engineering', 'exercise', 'Use Gemini Free to compare vague vs detailed prompts', 3, 45, TRUE, NULL),
('prompting-foundations-r4', 'prompting-foundations', 'prompt-engineering', 'quiz', 'Quiz: Identify the better prompt in given pairs', 4, NULL, FALSE, NULL),
('prompting-foundations-r5', 'prompting-foundations', 'prompt-engineering', 'project', 'Write 3 prompts for creative but controlled text (story, poem, explanation)', 5, NULL, TRUE, NULL)
ON CONFLICT (id) DO NOTHING;

-- Set file upload requirements for prompt-engineering exercises
UPDATE resources SET
    requires_upload = TRUE,
    accepted_file_types = ARRAY['text/plain', 'text/markdown', 'application/pdf', 'image/png', 'image/jpeg'],
    max_file_size_mb = 10
WHERE type IN ('exercise', 'project') AND pathway_id = 'prompt-engineering';

-- ============================================================================
-- 9. QUIZ METADATA EXAMPLES
-- ============================================================================
-- Quizzes store their questions/answers in the metadata JSONB field
-- This matches the frontend Quiz.tsx component format

-- Example quiz metadata for image-generation quiz
UPDATE resources SET
    metadata = '{
      "title": "Image Generation Model Types Quiz",
      "description": "Test your knowledge of AI image generation models and their use cases.",
      "passingScore": 70,
      "questions": [
        {
          "id": "q1",
          "type": "multiple-choice",
          "question": "Which AI image model is known for being open-source and highly customizable?",
          "options": [
            {"id": "a", "text": "DALL-E", "isCorrect": false},
            {"id": "b", "text": "Stable Diffusion", "isCorrect": true},
            {"id": "c", "text": "Midjourney", "isCorrect": false},
            {"id": "d", "text": "Imagen", "isCorrect": false}
          ],
          "explanation": "Stable Diffusion is open-source and allows for extensive customization through LoRAs, VAEs, and community models."
        },
        {
          "id": "q2",
          "type": "true-false",
          "question": "Gemini 2.5 Flash can edit existing images, not just generate new ones.",
          "options": [
            {"id": "true", "text": "True", "isCorrect": true},
            {"id": "false", "text": "False", "isCorrect": false}
          ],
          "explanation": "Gemini 2.5 Flash Image (Nano Banana) supports advanced image editing capabilities including background removal, pose alteration, and image fusion."
        }
      ]
    }'::jsonb
WHERE id = 'foundations-image-gen-r4';

-- Example quiz metadata for prompt-engineering quiz
UPDATE resources SET
    metadata = '{
      "title": "Prompting Fundamentals Quiz",
      "description": "Test your understanding of basic prompt engineering principles.",
      "passingScore": 70,
      "questions": [
        {
          "id": "q1",
          "type": "multiple-choice",
          "question": "What is the most important element of a good prompt?",
          "options": [
            {"id": "a", "text": "Making it as short as possible", "isCorrect": false},
            {"id": "b", "text": "Being clear and specific about what you want", "isCorrect": true},
            {"id": "c", "text": "Using complex technical language", "isCorrect": false},
            {"id": "d", "text": "Including emojis", "isCorrect": false}
          ],
          "explanation": "Clarity and specificity are crucial for getting accurate and relevant responses from AI models."
        },
        {
          "id": "q2",
          "type": "true-false",
          "question": "Few-shot learning involves providing examples in your prompt to guide the AI response.",
          "options": [
            {"id": "true", "text": "True", "isCorrect": true},
            {"id": "false", "text": "False", "isCorrect": false}
          ],
          "explanation": "Few-shot learning is a technique where you provide a few examples of the desired input-output pattern."
        }
      ]
    }'::jsonb
WHERE id = 'prompting-foundations-r4';

-- ============================================================================
-- CONFIGURATION SUMMARY
-- ============================================================================
-- File Retention: Files are kept forever (no automatic deletion)
-- Resubmission: Allowed after rejection (allow_resubmission = TRUE)
-- Max File Size: 50 MB (configurable per resource, with global max of 50 MB)
-- Grading: Simple pass/fail system
-- Email Notifications: Not implemented (future enhancement)
-- Quiz Format: Stored in resources.metadata JSONB field (matches Quiz.tsx component)

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
