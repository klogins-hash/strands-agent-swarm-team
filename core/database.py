"""
Database integration layer for PostgreSQL and Redis
Provides data persistence, caching, and vector storage capabilities.
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid

import asyncpg
import redis.asyncio as redis
import numpy as np
from dataclasses import asdict

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages PostgreSQL and Redis connections and operations."""
    
    def __init__(self):
        self.pg_pool: Optional[asyncpg.Pool] = None
        self.redis_client: Optional[redis.Redis] = None
        
        # Database configuration
        self.pg_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', '5432')),
            'database': os.getenv('POSTGRES_DB', 'strands_db'),
            'user': os.getenv('POSTGRES_USER', 'strands_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'strands_db_pass'),
            'min_size': 10,
            'max_size': 20
        }
        
        self.redis_config = {
            'host': os.getenv('REDIS_HOST', 'localhost'),
            'port': int(os.getenv('REDIS_PORT', '6379')),
            'password': os.getenv('REDIS_PASSWORD', 'strands_redis_pass'),
            'db': 0,
            'decode_responses': True
        }
    
    async def initialize(self):
        """Initialize database connections."""
        try:
            # Initialize PostgreSQL connection pool
            self.pg_pool = await asyncpg.create_pool(**self.pg_config)
            logger.info("PostgreSQL connection pool created")
            
            # Initialize Redis connection
            self.redis_client = redis.Redis(**self.redis_config)
            await self.redis_client.ping()
            logger.info("Redis connection established")
            
            # Test database connectivity
            await self._test_connections()
            
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            raise
    
    async def close(self):
        """Close database connections."""
        if self.pg_pool:
            await self.pg_pool.close()
            logger.info("PostgreSQL connection pool closed")
        
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    async def _test_connections(self):
        """Test database connections."""
        # Test PostgreSQL
        async with self.pg_pool.acquire() as conn:
            result = await conn.fetchval("SELECT 1")
            assert result == 1
        
        # Test Redis
        pong = await self.redis_client.ping()
        assert pong is True
        
        logger.info("Database connections tested successfully")

class AgentDataManager:
    """Manages agent and tool data persistence."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def save_agent(self, agent_data: Dict[str, Any]) -> str:
        """Save agent to database."""
        async with self.db.pg_pool.acquire() as conn:
            agent_id = str(uuid.uuid4())
            
            await conn.execute("""
                INSERT INTO agents.agents (id, name, description, system_prompt, specialization, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    system_prompt = EXCLUDED.system_prompt,
                    specialization = EXCLUDED.specialization,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            """, agent_id, agent_data['name'], agent_data.get('description'),
                agent_data.get('system_prompt'), agent_data.get('specialization'),
                json.dumps(agent_data.get('metadata', {})))
            
            logger.info(f"Saved agent: {agent_data['name']}")
            return agent_id
    
    async def save_tool(self, tool_data: Dict[str, Any]) -> str:
        """Save tool to database."""
        async with self.db.pg_pool.acquire() as conn:
            tool_id = str(uuid.uuid4())
            
            await conn.execute("""
                INSERT INTO agents.tools (id, name, description, parameters, implementation, dependencies)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (name) DO UPDATE SET
                    description = EXCLUDED.description,
                    parameters = EXCLUDED.parameters,
                    implementation = EXCLUDED.implementation,
                    dependencies = EXCLUDED.dependencies,
                    updated_at = NOW()
            """, tool_id, tool_data['name'], tool_data.get('description'),
                json.dumps(tool_data.get('parameters', {})),
                tool_data.get('implementation'), tool_data.get('dependencies', []))
            
            logger.info(f"Saved tool: {tool_data['name']}")
            return tool_id
    
    async def get_agent_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get agent by name."""
        async with self.db.pg_pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM agents.agents WHERE name = $1
            """, name)
            
            if row:
                return dict(row)
            return None
    
    async def get_all_agents(self) -> List[Dict[str, Any]]:
        """Get all agents."""
        async with self.db.pg_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM agents.agents ORDER BY created_at")
            return [dict(row) for row in rows]

class ProjectDataManager:
    """Manages project and task data persistence."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def save_project(self, project_data: Dict[str, Any]) -> str:
        """Save project to database."""
        async with self.db.pg_pool.acquire() as conn:
            project_id = project_data.get('id', str(uuid.uuid4()))
            
            await conn.execute("""
                INSERT INTO projects.projects 
                (id, name, description, status, priority, owner, start_date, due_date, 
                 budget_hours, spent_hours, tags, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    priority = EXCLUDED.priority,
                    start_date = EXCLUDED.start_date,
                    due_date = EXCLUDED.due_date,
                    budget_hours = EXCLUDED.budget_hours,
                    spent_hours = EXCLUDED.spent_hours,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            """, project_id, project_data['name'], project_data.get('description'),
                project_data.get('status', 'planning'), project_data.get('priority', 'medium'),
                project_data.get('owner'), project_data.get('start_date'),
                project_data.get('due_date'), project_data.get('budget_hours', 0.0),
                project_data.get('spent_hours', 0.0), project_data.get('tags', []),
                json.dumps(project_data.get('metadata', {})))
            
            logger.info(f"Saved project: {project_data['name']}")
            return project_id
    
    async def save_task(self, task_data: Dict[str, Any]) -> str:
        """Save task to database."""
        async with self.db.pg_pool.acquire() as conn:
            task_id = task_data.get('id', str(uuid.uuid4()))
            
            await conn.execute("""
                INSERT INTO projects.tasks 
                (id, project_id, title, description, status, priority, assigned_agents,
                 dependencies, estimated_hours, actual_hours, start_date, due_date,
                 completion_date, tags, notes)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    priority = EXCLUDED.priority,
                    assigned_agents = EXCLUDED.assigned_agents,
                    dependencies = EXCLUDED.dependencies,
                    estimated_hours = EXCLUDED.estimated_hours,
                    actual_hours = EXCLUDED.actual_hours,
                    start_date = EXCLUDED.start_date,
                    due_date = EXCLUDED.due_date,
                    completion_date = EXCLUDED.completion_date,
                    tags = EXCLUDED.tags,
                    notes = EXCLUDED.notes,
                    updated_at = NOW()
            """, task_id, task_data['project_id'], task_data['title'],
                task_data.get('description'), task_data.get('status', 'not_started'),
                task_data.get('priority', 'medium'), task_data.get('assigned_agents', []),
                task_data.get('dependencies', []), task_data.get('estimated_hours', 1.0),
                task_data.get('actual_hours', 0.0), task_data.get('start_date'),
                task_data.get('due_date'), task_data.get('completion_date'),
                task_data.get('tags', []), task_data.get('notes'))
            
            logger.info(f"Saved task: {task_data['title']}")
            return task_id
    
    async def get_project_with_tasks(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project with all its tasks."""
        async with self.db.pg_pool.acquire() as conn:
            # Get project
            project_row = await conn.fetchrow("""
                SELECT * FROM projects.projects WHERE id = $1
            """, project_id)
            
            if not project_row:
                return None
            
            project = dict(project_row)
            
            # Get tasks
            task_rows = await conn.fetch("""
                SELECT * FROM projects.tasks WHERE project_id = $1 ORDER BY created_at
            """, project_id)
            
            project['tasks'] = [dict(row) for row in task_rows]
            return project
    
    async def get_all_projects(self) -> List[Dict[str, Any]]:
        """Get all projects with basic info."""
        async with self.db.pg_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT p.*, 
                       COUNT(t.id) as task_count,
                       COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_tasks
                FROM projects.projects p
                LEFT JOIN projects.tasks t ON p.id = t.project_id
                GROUP BY p.id
                ORDER BY p.created_at DESC
            """)
            return [dict(row) for row in rows]

class ConversationDataManager:
    """Manages conversation and message data persistence."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def save_conversation(self, conversation_id: str, title: str = None, 
                              metadata: Dict[str, Any] = None) -> str:
        """Save conversation to database."""
        async with self.db.pg_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO conversations.conversations (id, title, metadata)
                VALUES ($1, $2, $3)
                ON CONFLICT (id) DO UPDATE SET
                    title = EXCLUDED.title,
                    metadata = EXCLUDED.metadata,
                    updated_at = NOW()
            """, conversation_id, title, json.dumps(metadata or {}))
            
            return conversation_id
    
    async def save_message(self, message_data: Dict[str, Any]) -> str:
        """Save message to database."""
        async with self.db.pg_pool.acquire() as conn:
            message_id = str(uuid.uuid4())
            
            await conn.execute("""
                INSERT INTO conversations.messages 
                (id, conversation_id, sender, content, message_type, timestamp, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, message_id, message_data['conversation_id'], message_data['sender'],
                message_data['content'], message_data.get('message_type', 'text'),
                message_data.get('timestamp', datetime.now()),
                json.dumps(message_data.get('metadata', {})))
            
            return message_id
    
    async def get_conversation_messages(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all messages for a conversation."""
        async with self.db.pg_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM conversations.messages 
                WHERE conversation_id = $1 
                ORDER BY timestamp
            """, conversation_id)
            return [dict(row) for row in rows]

class VectorDataManager:
    """Manages vector embeddings and similarity search."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    async def store_document_embedding(self, document_id: str, document_type: str,
                                     content: str, embedding: List[float],
                                     metadata: Dict[str, Any] = None) -> str:
        """Store document embedding."""
        async with self.db.pg_pool.acquire() as conn:
            embedding_id = str(uuid.uuid4())
            
            await conn.execute("""
                INSERT INTO vectors.document_embeddings 
                (id, document_id, document_type, content, embedding, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, embedding_id, document_id, document_type, content,
                embedding, json.dumps(metadata or {}))
            
            return embedding_id
    
    async def store_agent_memory(self, agent_id: str, memory_type: str,
                               content: str, embedding: List[float],
                               importance_score: float = 0.5,
                               metadata: Dict[str, Any] = None) -> str:
        """Store agent memory with embedding."""
        async with self.db.pg_pool.acquire() as conn:
            memory_id = str(uuid.uuid4())
            
            await conn.execute("""
                INSERT INTO vectors.agent_memory 
                (id, agent_id, memory_type, content, embedding, importance_score, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
            """, memory_id, agent_id, memory_type, content, embedding,
                importance_score, json.dumps(metadata or {}))
            
            return memory_id
    
    async def find_similar_documents(self, query_embedding: List[float],
                                   document_type: str = None,
                                   similarity_threshold: float = 0.7,
                                   max_results: int = 10) -> List[Dict[str, Any]]:
        """Find similar documents using vector similarity."""
        async with self.db.pg_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM find_similar_documents($1, $2, $3, $4)
            """, query_embedding, document_type, similarity_threshold, max_results)
            
            return [dict(row) for row in rows]
    
    async def get_agent_memories(self, agent_id: str, query_embedding: List[float],
                               memory_type: str = None,
                               similarity_threshold: float = 0.6,
                               max_results: int = 5) -> List[Dict[str, Any]]:
        """Get relevant agent memories using vector similarity."""
        async with self.db.pg_pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM get_agent_memories($1, $2, $3, $4, $5)
            """, agent_id, query_embedding, memory_type, similarity_threshold, max_results)
            
            return [dict(row) for row in rows]

class CacheManager:
    """Manages Redis caching operations."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.default_ttl = 3600  # 1 hour
    
    async def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """Set cache value."""
        try:
            serialized_value = json.dumps(value, default=str)
            ttl = ttl or self.default_ttl
            return await self.db.redis_client.setex(key, ttl, serialized_value)
        except Exception as e:
            logger.error(f"Cache set error: {e}")
            return False
    
    async def get(self, key: str) -> Any:
        """Get cache value."""
        try:
            value = await self.db.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    async def delete(self, key: str) -> bool:
        """Delete cache key."""
        try:
            return await self.db.redis_client.delete(key) > 0
        except Exception as e:
            logger.error(f"Cache delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if cache key exists."""
        try:
            return await self.db.redis_client.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error: {e}")
            return False
    
    async def set_hash(self, key: str, mapping: Dict[str, Any], ttl: int = None) -> bool:
        """Set hash cache value."""
        try:
            serialized_mapping = {k: json.dumps(v, default=str) for k, v in mapping.items()}
            result = await self.db.redis_client.hset(key, mapping=serialized_mapping)
            if ttl:
                await self.db.redis_client.expire(key, ttl)
            return result
        except Exception as e:
            logger.error(f"Cache hash set error: {e}")
            return False
    
    async def get_hash(self, key: str, field: str = None) -> Any:
        """Get hash cache value."""
        try:
            if field:
                value = await self.db.redis_client.hget(key, field)
                if value:
                    return json.loads(value)
            else:
                values = await self.db.redis_client.hgetall(key)
                if values:
                    return {k: json.loads(v) for k, v in values.items()}
            return None
        except Exception as e:
            logger.error(f"Cache hash get error: {e}")
            return None

# Global database manager instance
db_manager = DatabaseManager()
agent_data = AgentDataManager(db_manager)
project_data = ProjectDataManager(db_manager)
conversation_data = ConversationDataManager(db_manager)
vector_data = VectorDataManager(db_manager)
cache = CacheManager(db_manager)
