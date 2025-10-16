-- Migration to add missing modules for prompt-engineering and image-generation pathways
-- Date: 2025-10-16
-- Purpose: Fix 404 errors when completing modules in these pathways

\c aibc_db;

-- Insert modules for prompt-engineering pathway
INSERT INTO modules (id, pathway_id, title, description, order_index, duration_minutes) VALUES
('prompting-foundations', 'prompt-engineering', 'Prompting Foundations', 'Learn the basics of writing clear, effective prompts.', 1, 420),
('techniques-patterns', 'prompt-engineering', 'Techniques & Patterns (Builder)', 'Explore structured prompting techniques.', 2, 420),
('multimodal-structured', 'prompt-engineering', 'Multimodal & Structured Prompts (Innovator)', 'Move beyond text into multimodal and structured outputs.', 3, 630),
('prompt-engineering-capstone', 'prompt-engineering', 'Prompt Engineering Capstone (Creative Builder)', 'Apply prompt engineering to build a small, practical system.', 4, 420)
ON CONFLICT (id) DO NOTHING;

-- Insert modules for image-generation pathway
INSERT INTO modules (id, pathway_id, title, description, order_index, duration_minutes) VALUES
('foundations-image-gen', 'image-generation', 'Foundations of Image Generation', 'Understand types of AI image generation and foundational tools.', 1, 420),
('prompt-gemini-nano', 'image-generation', 'Prompt Engineering & Gemini Nano Banana (Builder)', 'Master prompt techniques and experiment with Google''s advanced image editor.', 2, 630),
('comfyui-workflows', 'image-generation', 'Workflow Design with ComfyUI & Web Community Tools (Builder)', 'Learn visual workflows for modular image generation.', 3, 630),
('lora-vae-finetuning', 'image-generation', 'Fine-Tuning with LoRA/VAE Techniques (Innovator)', 'Understand lightweight fine-tuning to specialize image generators.', 4, 630),
('saas-prototyping', 'image-generation', 'Monetizable SaaS Prototyping (Advanced Builder)', 'Build a simple Stripe-integrated image-gen web app for real-world use.', 5, 840),
('creative-service-capstone', 'image-generation', 'Pathway Capstone — Creative Image Service', 'Build an end-to-end image generation service with UI, prompt controls, and value.', 6, 840)
ON CONFLICT (id) DO NOTHING;

-- Verify the insertions
SELECT 'Prompt Engineering Modules:' as info;
SELECT id, title, order_index FROM modules WHERE pathway_id = 'prompt-engineering' ORDER BY order_index;

SELECT 'Image Generation Modules:' as info;
SELECT id, title, order_index FROM modules WHERE pathway_id = 'image-generation' ORDER BY order_index;

-- Show total module count per pathway
SELECT 'Module Count by Pathway:' as info;
SELECT pathway_id, COUNT(*) as module_count
FROM modules
GROUP BY pathway_id
ORDER BY pathway_id;
