-- Migration: Fix image MIME types and ensure JPG/JPEG/PNG support
-- Date: 2025-10-18
-- Purpose: Correct image/jpg to image/jpeg (proper MIME type standard)
--          and ensure all exercise/project resources properly support common image formats

\c aibc_db;

-- ============================================================================
-- FIX MIME TYPES
-- ============================================================================
-- NOTE: image/jpg is not a valid MIME type. The standard MIME type is image/jpeg
--       for both .jpg and .jpeg file extensions. Python's mimetypes.guess_type()
--       will return 'image/jpeg' for both extensions.

-- Remove incorrect 'image/jpg' and ensure 'image/jpeg' is present
-- This affects all resources that currently have image/jpg in their accepted types

-- For image-generation pathway: Fix MIME types
UPDATE resources SET
    accepted_file_types = ARRAY['image/png', 'image/jpeg', 'image/webp', 'application/pdf', 'text/plain']
WHERE pathway_id = 'image-generation'
  AND type IN ('exercise', 'project')
  AND 'image/jpg' = ANY(accepted_file_types);

-- For prompt-engineering pathway: Ensure proper MIME types
-- Keep text files primary, but fix image MIME types
UPDATE resources SET
    accepted_file_types = ARRAY['text/plain', 'text/markdown', 'application/pdf', 'image/png', 'image/jpeg', 'image/webp']
WHERE pathway_id = 'prompt-engineering'
  AND type IN ('exercise', 'project')
  AND ('image/jpg' = ANY(accepted_file_types) OR NOT 'image/webp' = ANY(accepted_file_types));

-- ============================================================================
-- ENSURE ALL UPLOAD RESOURCES HAVE FILE TYPES CONFIGURED
-- ============================================================================
-- Safety check: If any resources with requires_upload=TRUE don't have
-- accepted_file_types configured, set sensible defaults

-- Image-focused pathways get image defaults
UPDATE resources SET
    accepted_file_types = ARRAY['image/png', 'image/jpeg', 'image/webp', 'application/pdf'],
    max_file_size_mb = 25
WHERE pathway_id IN ('image-generation')
  AND type IN ('exercise', 'project')
  AND requires_upload = TRUE
  AND (accepted_file_types IS NULL OR array_length(accepted_file_types, 1) IS NULL);

-- Text-focused pathways get text + image defaults
UPDATE resources SET
    accepted_file_types = ARRAY['text/plain', 'text/markdown', 'application/pdf', 'image/png', 'image/jpeg'],
    max_file_size_mb = 10
WHERE pathway_id IN ('prompt-engineering')
  AND type IN ('exercise', 'project')
  AND requires_upload = TRUE
  AND (accepted_file_types IS NULL OR array_length(accepted_file_types, 1) IS NULL);

-- General fallback for any other pathways
UPDATE resources SET
    accepted_file_types = ARRAY['application/pdf', 'text/plain', 'image/png', 'image/jpeg'],
    max_file_size_mb = 25
WHERE type IN ('exercise', 'project')
  AND requires_upload = TRUE
  AND (accepted_file_types IS NULL OR array_length(accepted_file_types, 1) IS NULL);

-- ============================================================================
-- VERIFICATION
-- ============================================================================

-- Check that no resources have the incorrect 'image/jpg' MIME type
SELECT
    'Resources with incorrect image/jpg MIME type (should be 0):' as check_name,
    COUNT(*) as count
FROM resources
WHERE 'image/jpg' = ANY(accepted_file_types);

-- Verify image-generation pathway resources accept PNG/JPEG
SELECT
    'Image generation resources with PNG/JPEG support:' as check_name,
    COUNT(*) as count
FROM resources
WHERE pathway_id = 'image-generation'
  AND type IN ('exercise', 'project')
  AND 'image/png' = ANY(accepted_file_types)
  AND 'image/jpeg' = ANY(accepted_file_types);

-- Verify prompt-engineering pathway resources accept common formats
SELECT
    'Prompt engineering resources with proper file types:' as check_name,
    COUNT(*) as count
FROM resources
WHERE pathway_id = 'prompt-engineering'
  AND type IN ('exercise', 'project')
  AND 'text/plain' = ANY(accepted_file_types)
  AND 'image/png' = ANY(accepted_file_types)
  AND 'image/jpeg' = ANY(accepted_file_types);

-- Show sample of configured resources
SELECT
    id,
    pathway_id,
    type,
    title,
    accepted_file_types,
    max_file_size_mb
FROM resources
WHERE type IN ('exercise', 'project')
ORDER BY pathway_id, id
LIMIT 10;

-- Summary of all upload-enabled resources
WITH expanded_types AS (
    SELECT
        pathway_id,
        type,
        unnest(accepted_file_types) as file_type
    FROM resources
    WHERE requires_upload = TRUE
)
SELECT
    pathway_id,
    type,
    COUNT(DISTINCT file_type) as file_type_count,
    ARRAY_AGG(DISTINCT file_type ORDER BY file_type) as all_file_types_used
FROM expanded_types
GROUP BY pathway_id, type
ORDER BY pathway_id, type;
