-- Initialize Strands Agent Swarm Database
-- This script sets up the database schema with pgvector extension

-- Enable pgvector extension for vector storage
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS agents;
CREATE SCHEMA IF NOT EXISTS projects;
CREATE SCHEMA IF NOT EXISTS conversations;
CREATE SCHEMA IF NOT EXISTS vectors;

-- Agents and Tools Tables
CREATE TABLE IF NOT EXISTS agents.agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    system_prompt TEXT,
    specialization VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS agents.tools (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    parameters JSONB DEFAULT '{}'::jsonb,
    implementation TEXT,
    dependencies TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agents.agent_tools (
    agent_id UUID REFERENCES agents.agents(id) ON DELETE CASCADE,
    tool_id UUID REFERENCES agents.tools(id) ON DELETE CASCADE,
    PRIMARY KEY (agent_id, tool_id)
);

-- Projects and Tasks Tables
CREATE TABLE IF NOT EXISTS projects.projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'planning',
    priority VARCHAR(50) DEFAULT 'medium',
    owner VARCHAR(255),
    start_date TIMESTAMP WITH TIME ZONE,
    due_date TIMESTAMP WITH TIME ZONE,
    completion_date TIMESTAMP WITH TIME ZONE,
    budget_hours DECIMAL(10,2) DEFAULT 0.0,
    spent_hours DECIMAL(10,2) DEFAULT 0.0,
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS projects.tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects.projects(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'not_started',
    priority VARCHAR(50) DEFAULT 'medium',
    assigned_agents UUID[],
    dependencies UUID[],
    estimated_hours DECIMAL(8,2) DEFAULT 1.0,
    actual_hours DECIMAL(8,2) DEFAULT 0.0,
    start_date TIMESTAMP WITH TIME ZONE,
    due_date TIMESTAMP WITH TIME ZONE,
    completion_date TIMESTAMP WITH TIME ZONE,
    tags TEXT[],
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Conversations and Messages Tables
CREATE TABLE IF NOT EXISTS conversations.conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255),
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS conversations.messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations.conversations(id) ON DELETE CASCADE,
    sender VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    message_type VARCHAR(50) DEFAULT 'text',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Task Analysis and Execution Tables
CREATE TABLE IF NOT EXISTS conversations.task_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID,
    original_task TEXT NOT NULL,
    complexity VARCHAR(50),
    hitl_requirement VARCHAR(50),
    estimated_duration INTEGER,
    required_capabilities TEXT[],
    required_tools TEXT[],
    required_agents TEXT[],
    risk_factors TEXT[],
    success_criteria TEXT[],
    human_checkpoints TEXT[],
    confidence_score DECIMAL(3,2),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    analysis_data JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS conversations.task_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID,
    swarm_id VARCHAR(255),
    status VARCHAR(50) DEFAULT 'pending',
    start_time TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    end_time TIMESTAMP WITH TIME ZONE,
    execution_time_ms INTEGER,
    agents_used TEXT[],
    tools_created TEXT[],
    success BOOLEAN,
    error_message TEXT,
    result_data JSONB DEFAULT '{}'::jsonb,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Vector Storage Tables for Embeddings
CREATE TABLE IF NOT EXISTS vectors.document_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id VARCHAR(255) NOT NULL,
    document_type VARCHAR(100), -- 'task', 'conversation', 'project', 'agent_response'
    content TEXT NOT NULL,
    embedding vector(1536), -- OpenAI ada-002 dimension, adjust as needed
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vectors.agent_memory (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents.agents(id) ON DELETE CASCADE,
    memory_type VARCHAR(100), -- 'experience', 'knowledge', 'context'
    content TEXT NOT NULL,
    embedding vector(1536),
    importance_score DECIMAL(3,2) DEFAULT 0.5,
    access_count INTEGER DEFAULT 0,
    last_accessed TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Performance and Metrics Tables
CREATE TABLE IF NOT EXISTS agents.execution_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID REFERENCES agents.agents(id) ON DELETE CASCADE,
    task_id UUID,
    execution_time_ms INTEGER,
    tokens_used INTEGER,
    success BOOLEAN,
    error_type VARCHAR(100),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metrics_data JSONB DEFAULT '{}'::jsonb
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_agents_name ON agents.agents(name);
CREATE INDEX IF NOT EXISTS idx_agents_specialization ON agents.agents(specialization);
CREATE INDEX IF NOT EXISTS idx_tools_name ON agents.tools(name);

CREATE INDEX IF NOT EXISTS idx_projects_status ON projects.projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_priority ON projects.projects(priority);
CREATE INDEX IF NOT EXISTS idx_projects_owner ON projects.projects(owner);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects.projects(created_at);

CREATE INDEX IF NOT EXISTS idx_tasks_project_id ON projects.tasks(project_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON projects.tasks(status);
CREATE INDEX IF NOT EXISTS idx_tasks_priority ON projects.tasks(priority);
CREATE INDEX IF NOT EXISTS idx_tasks_due_date ON projects.tasks(due_date);

CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations.conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_created_at ON conversations.conversations(created_at);

CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON conversations.messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON conversations.messages(sender);
CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON conversations.messages(timestamp);

CREATE INDEX IF NOT EXISTS idx_task_analyses_task_id ON conversations.task_analyses(task_id);
CREATE INDEX IF NOT EXISTS idx_task_analyses_complexity ON conversations.task_analyses(complexity);

CREATE INDEX IF NOT EXISTS idx_task_executions_task_id ON conversations.task_executions(task_id);
CREATE INDEX IF NOT EXISTS idx_task_executions_status ON conversations.task_executions(status);
CREATE INDEX IF NOT EXISTS idx_task_executions_start_time ON conversations.task_executions(start_time);

-- Vector similarity search indexes
CREATE INDEX IF NOT EXISTS idx_document_embeddings_type ON vectors.document_embeddings(document_type);
CREATE INDEX IF NOT EXISTS idx_document_embeddings_vector ON vectors.document_embeddings USING ivfflat (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS idx_agent_memory_agent_id ON vectors.agent_memory(agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_memory_type ON vectors.agent_memory(memory_type);
CREATE INDEX IF NOT EXISTS idx_agent_memory_vector ON vectors.agent_memory USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_agent_memory_importance ON vectors.agent_memory(importance_score);

CREATE INDEX IF NOT EXISTS idx_execution_metrics_agent_id ON agents.execution_metrics(agent_id);
CREATE INDEX IF NOT EXISTS idx_execution_metrics_timestamp ON agents.execution_metrics(timestamp);

-- Create functions for common operations
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add triggers for updated_at columns
CREATE TRIGGER update_agents_updated_at BEFORE UPDATE ON agents.agents FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects.projects FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations.conversations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function for vector similarity search
CREATE OR REPLACE FUNCTION find_similar_documents(
    query_embedding vector(1536),
    doc_type VARCHAR(100) DEFAULT NULL,
    similarity_threshold FLOAT DEFAULT 0.7,
    max_results INTEGER DEFAULT 10
)
RETURNS TABLE (
    id UUID,
    document_id VARCHAR(255),
    document_type VARCHAR(100),
    content TEXT,
    similarity FLOAT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        de.id,
        de.document_id,
        de.document_type,
        de.content,
        (1 - (de.embedding <=> query_embedding)) as similarity,
        de.metadata
    FROM vectors.document_embeddings de
    WHERE 
        (doc_type IS NULL OR de.document_type = doc_type)
        AND (1 - (de.embedding <=> query_embedding)) > similarity_threshold
    ORDER BY de.embedding <=> query_embedding
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Function for agent memory retrieval
CREATE OR REPLACE FUNCTION get_agent_memories(
    agent_uuid UUID,
    query_embedding vector(1536),
    memory_type_filter VARCHAR(100) DEFAULT NULL,
    similarity_threshold FLOAT DEFAULT 0.6,
    max_results INTEGER DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    memory_type VARCHAR(100),
    content TEXT,
    similarity FLOAT,
    importance_score DECIMAL(3,2),
    access_count INTEGER,
    metadata JSONB
) AS $$
BEGIN
    -- Update access count for retrieved memories
    UPDATE vectors.agent_memory 
    SET access_count = access_count + 1, last_accessed = NOW()
    WHERE agent_id = agent_uuid;
    
    RETURN QUERY
    SELECT 
        am.id,
        am.memory_type,
        am.content,
        (1 - (am.embedding <=> query_embedding)) as similarity,
        am.importance_score,
        am.access_count,
        am.metadata
    FROM vectors.agent_memory am
    WHERE 
        am.agent_id = agent_uuid
        AND (memory_type_filter IS NULL OR am.memory_type = memory_type_filter)
        AND (1 - (am.embedding <=> query_embedding)) > similarity_threshold
    ORDER BY 
        (am.importance_score * (1 - (am.embedding <=> query_embedding))) DESC
    LIMIT max_results;
END;
$$ LANGUAGE plpgsql;

-- Insert some initial data
INSERT INTO agents.agents (name, description, specialization) VALUES
    ('researcher', 'Expert research agent for information gathering', 'research'),
    ('analyst', 'Data analysis and calculation specialist', 'analysis'),
    ('writer', 'Professional writing and documentation expert', 'writing'),
    ('coordinator', 'Task coordination and project management', 'coordination')
ON CONFLICT (name) DO NOTHING;

INSERT INTO agents.tools (name, description, parameters) VALUES
    ('web_search', 'Search the web for information', '{"query": "string"}'),
    ('calculate', 'Perform mathematical calculations', '{"expression": "string"}'),
    ('format_report', 'Create formatted reports', '{"title": "string", "content": "string"}'),
    ('file_processor', 'Process various file types', '{"file_path": "string"}')
ON CONFLICT (name) DO NOTHING;
