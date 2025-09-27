-- Database initialization for AI Bootcamp
-- Database already created by Docker environment variable

\c aibc_db;

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Users table with secure design
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE,
    account_status VARCHAR(50) DEFAULT 'active' CHECK (account_status IN ('active', 'suspended', 'deleted')),
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMP WITH TIME ZONE
);

-- Refresh tokens table for JWT management
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP WITH TIME ZONE,
    ip_address TEXT,
    user_agent TEXT
);

-- Email verification tokens
CREATE TABLE IF NOT EXISTS email_verification_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP WITH TIME ZONE
);

-- Password reset tokens
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    used_at TIMESTAMP WITH TIME ZONE
);

-- OAuth providers table
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

-- Audit log table for security
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(100),
    resource_id UUID,
    ip_address TEXT,
    user_agent TEXT,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Sessions table for active sessions management
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_token_hash ON refresh_tokens(token_hash);
CREATE INDEX idx_refresh_tokens_expires_at ON refresh_tokens(expires_at);
CREATE INDEX idx_sessions_user_id ON sessions(user_id);
CREATE INDEX idx_sessions_expires_at ON sessions(expires_at);
CREATE INDEX idx_oauth_accounts_user_id ON oauth_accounts(user_id);
CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_oauth_accounts_updated_at BEFORE UPDATE ON oauth_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to clean expired tokens
CREATE OR REPLACE FUNCTION clean_expired_tokens()
RETURNS void AS $$
BEGIN
    DELETE FROM refresh_tokens WHERE expires_at < CURRENT_TIMESTAMP;
    DELETE FROM email_verification_tokens WHERE expires_at < CURRENT_TIMESTAMP AND used_at IS NULL;
    DELETE FROM password_reset_tokens WHERE expires_at < CURRENT_TIMESTAMP AND used_at IS NULL;
    DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP;
END;
$$ language 'plpgsql';

-- Pathways table for storing pathway metadata
CREATE TABLE IF NOT EXISTS pathways (
    id VARCHAR(100) PRIMARY KEY,
    slug VARCHAR(100) UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    short_title VARCHAR(100) NOT NULL,
    instructor VARCHAR(255) NOT NULL,
    color VARCHAR(100) NOT NULL,
    total_modules INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Modules table for storing module information
CREATE TABLE IF NOT EXISTS modules (
    id VARCHAR(100) PRIMARY KEY,
    pathway_id VARCHAR(100) NOT NULL REFERENCES pathways(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    order_index INTEGER NOT NULL,
    duration_minutes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pathway_id, order_index)
);

-- User progress table for tracking user progress
CREATE TABLE IF NOT EXISTS user_progress (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pathway_id VARCHAR(100) NOT NULL REFERENCES pathways(id) ON DELETE CASCADE,
    current_module_id VARCHAR(100) REFERENCES modules(id) ON DELETE SET NULL,
    progress_percentage INTEGER DEFAULT 0 CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    completed_modules INTEGER DEFAULT 0,
    total_time_spent_minutes INTEGER DEFAULT 0,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_accessed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    UNIQUE(user_id, pathway_id)
);

-- Module completions table for tracking individual module completions
CREATE TABLE IF NOT EXISTS module_completions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    pathway_id VARCHAR(100) NOT NULL REFERENCES pathways(id) ON DELETE CASCADE,
    module_id VARCHAR(100) NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    time_spent_minutes INTEGER DEFAULT 0,
    UNIQUE(user_id, module_id)
);

-- Achievements table for storing achievement definitions
CREATE TABLE IF NOT EXISTS achievements (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    icon VARCHAR(100),
    category VARCHAR(50) NOT NULL CHECK (category IN ('pathway', 'module', 'streak', 'milestone', 'special')),
    requirement_type VARCHAR(50) NOT NULL CHECK (requirement_type IN ('pathways_completed', 'modules_completed', 'streak_days', 'time_spent', 'custom')),
    requirement_value INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- User achievements table for tracking earned achievements
CREATE TABLE IF NOT EXISTS user_achievements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_id VARCHAR(100) NOT NULL REFERENCES achievements(id) ON DELETE CASCADE,
    earned_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, achievement_id)
);

-- Learning streaks table for tracking daily learning streaks
CREATE TABLE IF NOT EXISTS learning_streaks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    current_streak INTEGER DEFAULT 0,
    longest_streak INTEGER DEFAULT 0,
    last_activity_date DATE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for progress tracking performance
CREATE INDEX idx_user_progress_user_id ON user_progress(user_id);
CREATE INDEX idx_user_progress_pathway_id ON user_progress(pathway_id);
CREATE INDEX idx_module_completions_user_id ON module_completions(user_id);
CREATE INDEX idx_module_completions_pathway_id ON module_completions(pathway_id);
CREATE INDEX idx_module_completions_module_id ON module_completions(module_id);
CREATE INDEX idx_user_achievements_user_id ON user_achievements(user_id);
CREATE INDEX idx_learning_streaks_user_id ON learning_streaks(user_id);
CREATE INDEX idx_modules_pathway_id ON modules(pathway_id);

-- Trigger for updating pathway updated_at
CREATE TRIGGER update_pathways_updated_at BEFORE UPDATE ON pathways
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for updating modules updated_at
CREATE TRIGGER update_modules_updated_at BEFORE UPDATE ON modules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial pathway data
INSERT INTO pathways (id, slug, title, short_title, instructor, color, total_modules) VALUES
('computer-vision', 'computer-vision', 'Computer Vision', 'Computer Vision', 'Olivier', 'from-blue-500 to-cyan-500', 8),
('reinforcement-learning', 'reinforcement-learning', 'Reinforcement Learning', 'RL', 'Roman', 'from-purple-500 to-pink-500', 10),
('mlops', 'mlops', 'MLops (Google Colab)', 'MLops', 'Olivier', 'from-green-500 to-emerald-500', 7),
('ai-ethics', 'ai-ethics', 'AI Ethics', 'AI Ethics', 'Sage', 'from-yellow-500 to-orange-500', 6),
('image-generation', 'image-generation', 'Image Generation / Artistic', 'Image Generation', 'Roman', 'from-rose-500 to-red-500', 9),
('llm-creation', 'llm-creation', 'LLM creation (Google Collab)', 'LLM Creation', 'Roman', 'from-indigo-500 to-purple-500', 8),
('ai-apis', 'ai-apis', 'APIs for AI (Python)', 'AI APIs', 'Olivier', 'from-teal-500 to-green-500', 6),
('devops', 'devops', 'DevOps (GitHub / GoogleCloud)', 'DevOps', 'Roman', 'from-slate-500 to-gray-500', 8),
('vibecoding', 'vibecoding', 'Vibecoding (Free tools, N8N)', 'Vibecoding', 'Roman', 'from-violet-500 to-purple-500', 5),
('prompt-engineering', 'prompt-engineering', 'Prompt Engineering', 'Prompt Engineering', 'Roman', 'from-amber-500 to-yellow-500', 7),
('ai-agents', 'ai-agents', 'AI Agents (MCP, Tooling)', 'AI Agents', 'Olivier', 'from-sky-500 to-blue-500', 9),
('vector-db-rag', 'vector-db-rag', 'Vector DB/RAG/Database', 'Vector DB/RAG', 'Olivier', 'from-emerald-500 to-teal-500', 8),
('ai-research', 'ai-research', 'AI research', 'AI Research', 'Roman', 'from-pink-500 to-rose-500', 10)
ON CONFLICT (id) DO NOTHING;

-- Insert sample modules for computer-vision pathway (as example)
INSERT INTO modules (id, pathway_id, title, description, order_index, duration_minutes) VALUES
('cv-intro', 'computer-vision', 'Introduction to Computer Vision', 'Learn the fundamentals of computer vision and image processing', 1, 45),
('cv-preprocessing', 'computer-vision', 'Image Preprocessing', 'Master techniques for preparing images for analysis', 2, 60),
('cv-feature-extraction', 'computer-vision', 'Feature Extraction', 'Understand how to extract meaningful features from images', 3, 75),
('cv-cnn-basics', 'computer-vision', 'CNN Fundamentals', 'Deep dive into Convolutional Neural Networks', 4, 90),
('cv-object-detection', 'computer-vision', 'Object Detection', 'Implement modern object detection algorithms', 5, 120),
('cv-segmentation', 'computer-vision', 'Image Segmentation', 'Learn semantic and instance segmentation techniques', 6, 90),
('cv-face-recognition', 'computer-vision', 'Face Recognition', 'Build face detection and recognition systems', 7, 75),
('cv-project', 'computer-vision', 'Capstone Project', 'Apply your knowledge in a real-world project', 8, 180),

-- AI Agents pathway modules
('agent-fundamentals', 'ai-agents', 'AI Agent Fundamentals', 'Understanding agent architectures and the foundations of autonomous AI systems.', 1, 50),
('mcp-protocol', 'ai-agents', 'Model Context Protocol (MCP)', 'Deep dive into MCP for building standardized agent-tool interactions.', 2, 75),
('tool-integration', 'ai-agents', 'Tool Integration & APIs', 'Connect agents with external services, databases, and APIs for expanded capabilities.', 3, 60),
('multi-agent-systems', 'ai-agents', 'Multi-Agent Systems', 'Design and coordinate multiple agents working together on complex tasks.', 4, 80),
('agent-deployment', 'ai-agents', 'Agent Deployment & Production', 'Deploy and scale AI agents in production environments.', 5, 90)
ON CONFLICT (id) DO NOTHING;

-- Insert initial achievements
INSERT INTO achievements (id, name, description, icon, category, requirement_type, requirement_value) VALUES
('first-module', 'First Step', 'Complete your first module', '🎯', 'module', 'modules_completed', 1),
('pathway-starter', 'Pathway Pioneer', 'Start your first pathway', '🚀', 'pathway', 'custom', 1),
('five-modules', 'Module Master', 'Complete 5 modules', '📚', 'module', 'modules_completed', 5),
('first-pathway', 'Pathway Complete', 'Complete your first pathway', '🏆', 'pathway', 'pathways_completed', 1),
('week-streak', 'Week Warrior', 'Maintain a 7-day learning streak', '🔥', 'streak', 'streak_days', 7),
('month-streak', 'Monthly Master', 'Maintain a 30-day learning streak', '💎', 'streak', 'streak_days', 30),
('ten-hours', 'Time Investor', 'Spend 10 hours learning', '⏰', 'milestone', 'time_spent', 600),
('three-pathways', 'Triple Threat', 'Complete 3 pathways', '🌟', 'pathway', 'pathways_completed', 3),
('speed-learner', 'Speed Learner', 'Complete a module in under 30 minutes', '⚡', 'special', 'custom', 30),
('all-pathways', 'AI Master', 'Complete all available pathways', '👑', 'pathway', 'pathways_completed', 13)
ON CONFLICT (id) DO NOTHING;

-- Grant permissions
GRANT ALL PRIVILEGES ON DATABASE aibc_db TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO postgres;