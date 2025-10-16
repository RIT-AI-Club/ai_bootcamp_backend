-- Migration: Populate resources for image-generation and prompt-engineering pathways
-- Date: 2025-10-16
-- Purpose: Add all resources from frontend JSON files to database for resource-level tracking

\c aibc_db;

-- ============================================================================
-- IMAGE GENERATION PATHWAY RESOURCES
-- ============================================================================

-- Module 1: foundations-image-gen
INSERT INTO resources (id, module_id, pathway_id, type, title, order_index, duration_minutes, requires_upload) VALUES
('foundations-image-gen-r1', 'foundations-image-gen', 'image-generation', 'video', 'What is AI Image Generation + Model Types', 1, 40, FALSE),
('foundations-image-gen-r2', 'foundations-image-gen', 'image-generation', 'article', 'Overview of Stable Diffusion, Imagen, DALL·E, Gemini (PDF)', 2, NULL, FALSE),
('foundations-image-gen-r3', 'foundations-image-gen', 'image-generation', 'exercise', 'Simple Stable Diffusion prompt generation (Colab)', 3, 45, TRUE),
('foundations-image-gen-r4', 'foundations-image-gen', 'image-generation', 'quiz', 'Quiz: 8 MCQ on model types and use-cases', 4, NULL, FALSE),
('foundations-image-gen-r5', 'foundations-image-gen', 'image-generation', 'project', 'Generate 3 mood-board images for fictional product', 5, NULL, TRUE)
ON CONFLICT (id) DO NOTHING;

-- Module 2: prompt-gemini-nano
INSERT INTO resources (id, module_id, pathway_id, type, title, order_index, duration_minutes, requires_upload) VALUES
('prompt-gemini-nano-r1', 'prompt-gemini-nano', 'image-generation', 'video', 'Prompt Crafting + Intro to Gemini Nano Banana', 1, 50, FALSE),
('prompt-gemini-nano-r2', 'prompt-gemini-nano', 'image-generation', 'article', 'Gemini 2.5 Flash Image capabilities guide', 2, NULL, FALSE),
('prompt-gemini-nano-r3', 'prompt-gemini-nano', 'image-generation', 'exercise', 'Use Gemini via AI Studio for image editing', 3, 60, TRUE),
('prompt-gemini-nano-r4', 'prompt-gemini-nano', 'image-generation', 'quiz', 'Quiz: Identify best prompts for Gemini tasks', 4, NULL, FALSE),
('prompt-gemini-nano-r5', 'prompt-gemini-nano', 'image-generation', 'project', 'Design product mockup with Gemini (upload, edit background, alter pose)', 5, NULL, TRUE)
ON CONFLICT (id) DO NOTHING;

-- Module 3: comfyui-workflows
INSERT INTO resources (id, module_id, pathway_id, type, title, order_index, duration_minutes, requires_upload) VALUES
('comfyui-workflows-r1', 'comfyui-workflows', 'image-generation', 'video', 'ComfyUI walkthrough—nodes, pipelines, community models', 1, 60, FALSE),
('comfyui-workflows-r2', 'comfyui-workflows', 'image-generation', 'article', 'Guide to Hugging Face Playground & Model Hubs (PDF)', 2, NULL, FALSE),
('comfyui-workflows-r3', 'comfyui-workflows', 'image-generation', 'exercise', 'Build ComfyUI flow with LoRA style and VAE upscaling', 3, 90, TRUE),
('comfyui-workflows-r4', 'comfyui-workflows', 'image-generation', 'quiz', 'Quiz: Match node functions (CLIP encode, LoRA apply)', 4, NULL, FALSE),
('comfyui-workflows-r5', 'comfyui-workflows', 'image-generation', 'project', 'Create reusable ComfyUI pipeline and share config', 5, NULL, TRUE)
ON CONFLICT (id) DO NOTHING;

-- Module 4: lora-vae-finetuning
INSERT INTO resources (id, module_id, pathway_id, type, title, order_index, duration_minutes, requires_upload) VALUES
('lora-vae-finetuning-r1', 'lora-vae-finetuning', 'image-generation', 'video', 'How LoRA and VAE enable personalization', 1, 55, FALSE),
('lora-vae-finetuning-r2', 'lora-vae-finetuning', 'image-generation', 'article', 'Examples of stylized models and ethical considerations (PDF)', 2, NULL, FALSE),
('lora-vae-finetuning-r3', 'lora-vae-finetuning', 'image-generation', 'exercise', 'Apply LoRA to base model for unique art style (Colab)', 3, 120, TRUE),
('lora-vae-finetuning-r4', 'lora-vae-finetuning', 'image-generation', 'quiz', 'Quiz: Differences between full model vs LoRA fine-tuning', 4, NULL, FALSE),
('lora-vae-finetuning-r5', 'lora-vae-finetuning', 'image-generation', 'project', 'Train/apply LoRA for specific theme (anime, architecture)', 5, NULL, TRUE)
ON CONFLICT (id) DO NOTHING;

-- Module 5: saas-prototyping
INSERT INTO resources (id, module_id, pathway_id, type, title, order_index, duration_minutes, requires_upload) VALUES
('saas-prototyping-r1', 'saas-prototyping', 'image-generation', 'video', 'Prototyping monetizable workflows with Flask or Streamlit', 1, 70, FALSE),
('saas-prototyping-r2', 'saas-prototyping', 'image-generation', 'article', 'Case study—AI-generated ecommerce mockup service (PDF)', 2, NULL, FALSE),
('saas-prototyping-r3', 'saas-prototyping', 'image-generation', 'exercise', 'Deploy image generation via Gradio/Flask (Colab)', 3, 90, TRUE),
('saas-prototyping-r4', 'saas-prototyping', 'image-generation', 'quiz', 'Quiz: Identify app security requirements', 4, NULL, FALSE),
('saas-prototyping-r5', 'saas-prototyping', 'image-generation', 'project', 'Prototype web interface with prompt upload and image delivery', 5, NULL, TRUE)
ON CONFLICT (id) DO NOTHING;

-- Module 6: creative-service-capstone
INSERT INTO resources (id, module_id, pathway_id, type, title, order_index, duration_minutes, requires_upload) VALUES
('creative-service-capstone-r1', 'creative-service-capstone', 'image-generation', 'video', 'Bringing it all together—design, deployment, UX', 1, 80, FALSE),
('creative-service-capstone-r2', 'creative-service-capstone', 'image-generation', 'article', 'Ethical deployment, watermarking, and avoiding misuse (PDF)', 2, NULL, FALSE),
('creative-service-capstone-r3', 'creative-service-capstone', 'image-generation', 'exercise', 'Deploy via Hugging Face Spaces with Stable Diffusion', 3, 120, TRUE),
('creative-service-capstone-r4', 'creative-service-capstone', 'image-generation', 'quiz', 'Quiz: Ethical scenarios and watermark policies', 4, NULL, FALSE),
('creative-service-capstone-r5', 'creative-service-capstone', 'image-generation', 'project', 'Capstone: Choose from meme generator, avatar service, or mockup generator', 5, NULL, TRUE)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- PROMPT ENGINEERING PATHWAY RESOURCES
-- ============================================================================

-- Module 1: prompting-foundations
INSERT INTO resources (id, module_id, pathway_id, type, title, order_index, duration_minutes, requires_upload) VALUES
('prompting-foundations-r1', 'prompting-foundations', 'prompt-engineering', 'video', 'Why Prompts Matter — Talking to AI', 1, 35, FALSE),
('prompting-foundations-r2', 'prompting-foundations', 'prompt-engineering', 'article', 'Good vs Bad Prompts Examples (PDF)', 2, NULL, FALSE),
('prompting-foundations-r3', 'prompting-foundations', 'prompt-engineering', 'exercise', 'Use Gemini Free to compare vague vs detailed prompts', 3, 45, TRUE),
('prompting-foundations-r4', 'prompting-foundations', 'prompt-engineering', 'quiz', 'Quiz: Identify the better prompt in given pairs', 4, NULL, FALSE),
('prompting-foundations-r5', 'prompting-foundations', 'prompt-engineering', 'project', 'Write 3 prompts for creative but controlled text (story, poem, explanation)', 5, NULL, TRUE)
ON CONFLICT (id) DO NOTHING;

-- Module 2: techniques-patterns
INSERT INTO resources (id, module_id, pathway_id, type, title, order_index, duration_minutes, requires_upload) VALUES
('techniques-patterns-r1', 'techniques-patterns', 'prompt-engineering', 'video', 'Prompt Patterns — Few-Shot, Chain-of-Thought, Role Prompts', 1, 50, FALSE),
('techniques-patterns-r2', 'techniques-patterns', 'prompt-engineering', 'article', 'Prompting Techniques Cheat Sheet (PDF)', 2, NULL, FALSE),
('techniques-patterns-r3', 'techniques-patterns', 'prompt-engineering', 'exercise', 'Test prompts to GPT/Claude in Colab, compare outputs', 3, 90, TRUE),
('techniques-patterns-r4', 'techniques-patterns', 'prompt-engineering', 'quiz', 'Quiz: Match technique to its example', 4, NULL, FALSE),
('techniques-patterns-r5', 'techniques-patterns', 'prompt-engineering', 'project', 'Design prompt template: model acts as teacher explaining math in 3 difficulty levels', 5, NULL, TRUE)
ON CONFLICT (id) DO NOTHING;

-- Module 3: multimodal-structured
INSERT INTO resources (id, module_id, pathway_id, type, title, order_index, duration_minutes, requires_upload) VALUES
('multimodal-structured-r1', 'multimodal-structured', 'prompt-engineering', 'video', 'Multimodal Prompting — Images, Audio, JSON Outputs', 1, 60, FALSE),
('multimodal-structured-r2', 'multimodal-structured', 'prompt-engineering', 'article', 'How to Force JSON or CSV Output with LLMs (PDF)', 2, NULL, FALSE),
('multimodal-structured-r3', 'multimodal-structured', 'prompt-engineering', 'exercise', 'Use Gemini/OpenAI CLI for structured JSON + image prompts', 3, 120, TRUE),
('multimodal-structured-r4', 'multimodal-structured', 'prompt-engineering', 'quiz', 'Quiz: Why are schemas useful in prompts?', 4, NULL, FALSE),
('multimodal-structured-r5', 'multimodal-structured', 'prompt-engineering', 'project', 'Create prompt: product description → formatted JSON spec + matching image', 5, NULL, TRUE)
ON CONFLICT (id) DO NOTHING;

-- Module 4: prompt-engineering-capstone
INSERT INTO resources (id, module_id, pathway_id, type, title, order_index, duration_minutes, requires_upload) VALUES
('prompt-engineering-capstone-r1', 'prompt-engineering-capstone', 'prompt-engineering', 'video', 'From Prompt to Product', 1, 55, FALSE),
('prompt-engineering-capstone-r2', 'prompt-engineering-capstone', 'prompt-engineering', 'article', 'Case Studies — Prompt Engineering in Startups & Research (PDF)', 2, NULL, FALSE),
('prompt-engineering-capstone-r3', 'prompt-engineering-capstone', 'prompt-engineering', 'exercise', 'Combine structured prompt + API/CLI tool integration', 3, 120, TRUE),
('prompt-engineering-capstone-r4', 'prompt-engineering-capstone', 'prompt-engineering', 'quiz', 'Quiz: Risks of prompts vs fine-tuning reflection', 4, NULL, FALSE),
('prompt-engineering-capstone-r5', 'prompt-engineering-capstone', 'prompt-engineering', 'project', 'Capstone: Choose from Q&A bot, image+caption generator, or study flashcard tool', 5, NULL, TRUE)
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- SET FILE UPLOAD REQUIREMENTS
-- ============================================================================

-- Image generation pathway: exercises and projects accept images and PDFs
UPDATE resources SET
    accepted_file_types = ARRAY['image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'application/pdf', 'text/plain'],
    max_file_size_mb = 25
WHERE pathway_id = 'image-generation' AND type IN ('exercise', 'project');

-- Prompt engineering pathway: exercises and projects accept text and PDFs
UPDATE resources SET
    accepted_file_types = ARRAY['text/plain', 'text/markdown', 'application/pdf', 'image/png', 'image/jpeg'],
    max_file_size_mb = 10
WHERE pathway_id = 'prompt-engineering' AND type IN ('exercise', 'project');

-- ============================================================================
-- VERIFICATION
-- ============================================================================

SELECT 'Image Generation Resources:' as info;
SELECT module_id, COUNT(*) as resource_count
FROM resources
WHERE pathway_id = 'image-generation'
GROUP BY module_id
ORDER BY module_id;

SELECT 'Prompt Engineering Resources:' as info;
SELECT module_id, COUNT(*) as resource_count
FROM resources
WHERE pathway_id = 'prompt-engineering'
GROUP BY module_id
ORDER BY module_id;

SELECT 'Total Resources Added:' as info;
SELECT COUNT(*) as total FROM resources WHERE pathway_id IN ('image-generation', 'prompt-engineering');
