"""
Web Dashboard for Strands Agent Swarm Team
Provides conversation management, task approval, and observability.
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import asdict
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.simple_agent import SimpleSwarm, create_basic_swarm, AgentTemplates
from core.project_manager import ProjectManager, Priority, ProjectStatus, TaskStatus
from core.groq_model import get_groq_model
try:
    from core.database import (
        db_manager, agent_data, project_data, conversation_data, 
        vector_data, cache
    )
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    logger.warning("Database modules not available, running without persistence")

logger = logging.getLogger(__name__)

# Pydantic models for API
class TaskRequest(BaseModel):
    task: str
    priority: str = "medium"
    metadata: Dict[str, Any] = {}

class TaskApproval(BaseModel):
    task_id: str
    approved: bool
    feedback: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None

class ConversationMessage(BaseModel):
    id: str
    task_id: str
    timestamp: datetime
    sender: str  # 'user', 'system', 'agent'
    content: str
    message_type: str  # 'task', 'approval', 'feedback', 'result'
    metadata: Dict[str, Any] = {}

# Application state
class AppState:
    def __init__(self):
        self.conversations: Dict[str, List[ConversationMessage]] = {}
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.active_connections: List[WebSocket] = []
        self.swarm = create_basic_swarm()
        self.project_manager = ProjectManager()
        self.groq_model = get_groq_model()

app = FastAPI(title="Strands Agent Swarm Dashboard")
app.mount("/static", StaticFiles(directory="web/static"), name="static")
templates = Jinja2Templates(directory="web/templates")

# Global state
state = AppState()

@app.on_event("startup")
async def startup_event():
    """Initialize system on startup."""
    try:
        if DATABASE_AVAILABLE:
            await db_manager.initialize()
            logger.info("Database connections initialized")
        else:
            logger.info("Running without database persistence")
        
        # Test Groq connection
        health = await state.groq_model.health_check()
        if health:
            logger.info("Groq API connection verified")
        else:
            logger.warning("Groq API connection failed")
            
    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Close connections on shutdown."""
    try:
        if DATABASE_AVAILABLE:
            await db_manager.close()
            logger.info("Database connections closed")
        logger.info("System shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove dead connections
                self.active_connections.remove(connection)

manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "conversations": list(state.conversations.keys()),
        "active_tasks": len([t for t in state.tasks.values() if t.get("status") == "active"])
    })

@app.get("/projects", response_class=HTMLResponse)
async def projects_dashboard(request: Request):
    """Project management dashboard page."""
    return templates.TemplateResponse("projects.html", {
        "request": request
    })

@app.get("/api/conversations")
async def get_conversations():
    """Get all conversations."""
    return {
        "conversations": [
            {
                "id": conv_id,
                "title": messages[0].content[:50] + "..." if messages else "Empty",
                "last_message": messages[-1].timestamp if messages else None,
                "message_count": len(messages),
                "status": state.tasks.get(conv_id, {}).get("status", "unknown")
            }
            for conv_id, messages in state.conversations.items()
        ]
    }

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get specific conversation."""
    if conversation_id not in state.conversations:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages = []
    for msg in state.conversations[conversation_id]:
        if hasattr(msg, '__dict__'):
            # Convert dataclass to dict manually
            messages.append({
                "id": getattr(msg, 'id', ''),
                "task_id": getattr(msg, 'task_id', ''),
                "timestamp": getattr(msg, 'timestamp', ''),
                "sender": getattr(msg, 'sender', ''),
                "content": getattr(msg, 'content', ''),
                "message_type": getattr(msg, 'message_type', ''),
                "metadata": getattr(msg, 'metadata', {})
            })
        else:
            # Already a dict
            messages.append(msg)
    
    return {
        "id": conversation_id,
        "messages": messages,
        "task_info": state.tasks.get(conversation_id, {})
    }

@app.post("/api/tasks")
async def create_task(task_request: TaskRequest):
    """Create a new task and start analysis."""
    task_id = str(uuid.uuid4())
    
    # Create conversation
    initial_message = ConversationMessage(
        id=str(uuid.uuid4()),
        task_id=task_id,
        timestamp=datetime.now(),
        sender="user",
        content=task_request.task,
        message_type="task",
        metadata=task_request.metadata
    )
    
    state.conversations[task_id] = [initial_message]
    
    # Start task analysis using the swarm
    try:
        # Use the coordinator agent to analyze the task
        result = await state.swarm.execute_task(task_request.task, "coordinator")
        
        # Store task information
        state.tasks[task_id] = {
            "id": task_id,
            "original_task": task_request.task,
            "priority": task_request.priority,
            "status": "analyzed",
            "result": result,
            "created_at": datetime.now().isoformat(),
            "metadata": task_request.metadata
        }
        
        # Add analysis messages to conversation
        for agent_name, response in result.get("responses", {}).items():
            analysis_message = ConversationMessage(
                id=str(uuid.uuid4()),
                task_id=task_id,
                timestamp=datetime.now(),
                sender=agent_name,
                content=response,
                message_type="analysis",
                metadata={"agent_role": agent_name}
            )
            state.conversations[task_id].append(analysis_message)
        
        # Broadcast update
        await manager.broadcast(json.dumps({
            "type": "task_created",
            "task_id": task_id,
            "result": result
        }))
        
        return {"task_id": task_id, "status": "created", "result": result}
        
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/tasks/{task_id}/approve")
async def approve_task(task_id: str, approval: TaskApproval):
    """Approve or reject a task."""
    if task_id not in state.tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = state.tasks[task_id]
    
    if approval.approved:
        task["status"] = "approved"
        
        # Add approval message
        approval_message = ConversationMessage(
            id=str(uuid.uuid4()),
            task_id=task_id,
            timestamp=datetime.now(),
            sender="user",
            content=f"Task approved. {approval.feedback or 'No additional feedback.'}",
            message_type="approval",
            metadata={"approved": True, "modifications": approval.modifications}
        )
        
        state.conversations[task_id].append(approval_message)
        
        # Start task execution
        asyncio.create_task(execute_task(task_id, approval.modifications))
        
    else:
        task["status"] = "rejected"
        
        # Add rejection message
        rejection_message = ConversationMessage(
            id=str(uuid.uuid4()),
            task_id=task_id,
            timestamp=datetime.now(),
            sender="user",
            content=f"Task rejected. {approval.feedback or 'No feedback provided.'}",
            message_type="rejection",
            metadata={"approved": False, "feedback": approval.feedback}
        )
        
        state.conversations[task_id].append(rejection_message)
    
    # Broadcast update
    await manager.broadcast(json.dumps({
        "type": "task_approval",
        "task_id": task_id,
        "approved": approval.approved,
        "status": task["status"]
    }))
    
    return {"status": "success", "task_status": task["status"]}

async def execute_task(task_id: str, modifications: Optional[Dict[str, Any]] = None):
    """Execute an approved task."""
    try:
        task = state.tasks[task_id]
        task["status"] = "executing"
        
        # Add execution start message
        start_message = ConversationMessage(
            id=str(uuid.uuid4()),
            task_id=task_id,
            timestamp=datetime.now(),
            sender="system",
            content="Task execution started. Building required agents and tools...",
            message_type="execution_start",
            metadata={}
        )
        
        state.conversations[task_id].append(start_message)
        
        # Broadcast update
        await manager.broadcast(json.dumps({
            "type": "execution_start",
            "task_id": task_id
        }))
        
        # Execute task using orchestrator
        result = await state.orchestrator.execute_task(
            task_id=task_id,
            task=task["original_task"],
            analysis=task["analysis"],
            modifications=modifications
        )
        
        task["status"] = "completed"
        task["result"] = result
        
        # Add completion message
        completion_message = ConversationMessage(
            id=str(uuid.uuid4()),
            task_id=task_id,
            timestamp=datetime.now(),
            sender="system",
            content="Task completed successfully!",
            message_type="completion",
            metadata={"result": result}
        )
        
        state.conversations[task_id].append(completion_message)
        
        # Broadcast completion
        await manager.broadcast(json.dumps({
            "type": "task_completed",
            "task_id": task_id,
            "result": result
        }))
        
    except Exception as e:
        logger.error(f"Error executing task {task_id}: {e}")
        
        task["status"] = "failed"
        task["error"] = str(e)
        
        # Add error message
        error_message = ConversationMessage(
            id=str(uuid.uuid4()),
            task_id=task_id,
            timestamp=datetime.now(),
            sender="system",
            content=f"Task execution failed: {str(e)}",
            message_type="error",
            metadata={"error": str(e)}
        )
        
        state.conversations[task_id].append(error_message)
        
        # Broadcast error
        await manager.broadcast(json.dumps({
            "type": "task_failed",
            "task_id": task_id,
            "error": str(e)
        }))

@app.get("/api/metrics")
async def get_metrics():
    """Get system metrics and observability data."""
    total_tasks = len(state.tasks)
    completed_tasks = len([t for t in state.tasks.values() if t.get("status") == "completed"])
    active_tasks = len([t for t in state.tasks.values() if t.get("status") in ["analyzing", "approved", "executing"]])
    failed_tasks = len([t for t in state.tasks.values() if t.get("status") == "failed"])
    
    return {
        "tasks": {
            "total": total_tasks,
            "completed": completed_tasks,
            "active": active_tasks,
            "failed": failed_tasks,
            "success_rate": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        },
        "conversations": {
            "total": len(state.conversations),
            "active": len([c for c in state.conversations.values() if len(c) > 0])
        },
        "agents": {
            "total": len(state.swarm.agents),
            "active": len(state.swarm.agents),
            "swarm_info": state.swarm.get_swarm_info()
        },
        "projects": {
            "total": len(state.project_manager.projects),
            "active": len([p for p in state.project_manager.projects.values() if p.status.value == "active"]),
            "completed": len([p for p in state.project_manager.projects.values() if p.status.value == "completed"])
        }
    }

# Project Management API Endpoints
@app.get("/api/projects")
async def get_projects():
    """Get all projects with metrics."""
    return state.project_manager.get_dashboard_data()

@app.post("/api/projects")
async def create_project(project_data: dict):
    """Create a new project."""
    try:
        project_id = state.project_manager.create_project(
            name=project_data["name"],
            description=project_data["description"],
            owner=project_data.get("owner", "user"),
            priority=Priority(project_data.get("priority", "medium")),
            budget_hours=project_data.get("budget_hours", 0.0)
        )
        
        return {"project_id": project_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/projects/{project_id}/tasks")
async def add_task_to_project(project_id: str, task_data: dict):
    """Add a task to a project."""
    try:
        task_id = state.project_manager.add_task_to_project(
            project_id=project_id,
            title=task_data["title"],
            description=task_data["description"],
            priority=Priority(task_data.get("priority", "medium")),
            estimated_hours=task_data.get("estimated_hours", 1.0),
            dependencies=task_data.get("dependencies", []),
            assigned_agents=task_data.get("assigned_agents", []),
            tags=task_data.get("tags", [])
        )
        
        return {"task_id": task_id, "status": "created"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/projects/{project_id}/tasks/{task_id}/status")
async def update_task_status(project_id: str, task_id: str, status_data: dict):
    """Update task status."""
    try:
        state.project_manager.update_task_status(
            project_id=project_id,
            task_id=task_id,
            status=TaskStatus(status_data["status"])
        )
        
        return {"status": "updated"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/projects/{project_id}/tasks/{task_id}/time")
async def log_time(project_id: str, task_id: str, time_data: dict):
    """Log time spent on a task."""
    try:
        state.project_manager.log_time(
            project_id=project_id,
            task_id=task_id,
            hours=time_data["hours"]
        )
        
        return {"status": "logged"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/projects/{project_id}/metrics")
async def get_project_metrics(project_id: str):
    """Get detailed metrics for a specific project."""
    try:
        metrics = state.project_manager.get_project_metrics(project_id)
        return asdict(metrics)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/projects/{project_id}/critical-path")
async def get_critical_path(project_id: str):
    """Get critical path for a project."""
    try:
        critical_path = state.project_manager.get_critical_path(project_id)
        return {"critical_path": [asdict(task) for task in critical_path]}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/resources")
async def get_resource_utilization():
    """Get resource utilization across all projects."""
    return state.project_manager.get_resource_utilization()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming WebSocket messages if needed
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
