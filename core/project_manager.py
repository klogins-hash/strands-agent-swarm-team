"""
Project Management System
Manages projects, tracks dependencies, timelines, and resource allocation.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import uuid

logger = logging.getLogger(__name__)

class ProjectStatus(Enum):
    PLANNING = "planning"
    ACTIVE = "active"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class TaskStatus(Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ProjectTask:
    """Individual task within a project."""
    id: str
    title: str
    description: str
    status: TaskStatus
    priority: Priority
    assigned_agents: List[str]
    dependencies: List[str]  # Task IDs this task depends on
    estimated_hours: float
    actual_hours: float = 0.0
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class Project:
    """Project containing multiple tasks."""
    id: str
    name: str
    description: str
    status: ProjectStatus
    priority: Priority
    owner: str
    tasks: Dict[str, ProjectTask] = field(default_factory=dict)
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    budget_hours: float = 0.0
    spent_hours: float = 0.0
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

@dataclass
class ResourceAllocation:
    """Resource allocation tracking."""
    agent_id: str
    project_id: str
    task_id: str
    allocated_hours: float
    start_date: datetime
    end_date: datetime
    utilization_percentage: float = 0.0

@dataclass
class ProjectMetrics:
    """Project performance metrics."""
    project_id: str
    completion_percentage: float
    tasks_completed: int
    tasks_total: int
    hours_spent: float
    hours_estimated: float
    days_remaining: int
    is_on_schedule: bool
    blocked_tasks: int
    overdue_tasks: int

class ProjectManager:
    """Manages projects, tasks, and resources."""
    
    def __init__(self):
        self.projects: Dict[str, Project] = {}
        self.resource_allocations: List[ResourceAllocation] = []
        
    def create_project(
        self,
        name: str,
        description: str,
        owner: str,
        priority: Priority = Priority.MEDIUM,
        start_date: Optional[datetime] = None,
        due_date: Optional[datetime] = None,
        budget_hours: float = 0.0
    ) -> str:
        """Create a new project."""
        project_id = str(uuid.uuid4())
        
        project = Project(
            id=project_id,
            name=name,
            description=description,
            status=ProjectStatus.PLANNING,
            priority=priority,
            owner=owner,
            start_date=start_date,
            due_date=due_date,
            budget_hours=budget_hours
        )
        
        self.projects[project_id] = project
        logger.info(f"Created project: {name} ({project_id})")
        
        return project_id
    
    def add_task_to_project(
        self,
        project_id: str,
        title: str,
        description: str,
        priority: Priority = Priority.MEDIUM,
        estimated_hours: float = 1.0,
        dependencies: List[str] = None,
        assigned_agents: List[str] = None,
        due_date: Optional[datetime] = None,
        tags: List[str] = None
    ) -> str:
        """Add a task to a project."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        task_id = str(uuid.uuid4())
        
        task = ProjectTask(
            id=task_id,
            title=title,
            description=description,
            status=TaskStatus.NOT_STARTED,
            priority=priority,
            assigned_agents=assigned_agents or [],
            dependencies=dependencies or [],
            estimated_hours=estimated_hours,
            due_date=due_date,
            tags=tags or []
        )
        
        self.projects[project_id].tasks[task_id] = task
        self.projects[project_id].updated_at = datetime.now()
        
        logger.info(f"Added task '{title}' to project {project_id}")
        return task_id
    
    def update_task_status(self, project_id: str, task_id: str, status: TaskStatus) -> None:
        """Update task status."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        if task_id not in self.projects[project_id].tasks:
            raise ValueError(f"Task {task_id} not found in project {project_id}")
        
        task = self.projects[project_id].tasks[task_id]
        old_status = task.status
        task.status = status
        task.updated_at = datetime.now()
        
        # Set completion date if completed
        if status == TaskStatus.COMPLETED and old_status != TaskStatus.COMPLETED:
            task.completion_date = datetime.now()
        
        # Update project status if all tasks completed
        if self._all_tasks_completed(project_id):
            self.projects[project_id].status = ProjectStatus.COMPLETED
            self.projects[project_id].completion_date = datetime.now()
        
        logger.info(f"Updated task {task_id} status: {old_status.value} -> {status.value}")
    
    def log_time(self, project_id: str, task_id: str, hours: float) -> None:
        """Log time spent on a task."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        if task_id not in self.projects[project_id].tasks:
            raise ValueError(f"Task {task_id} not found in project {project_id}")
        
        task = self.projects[project_id].tasks[task_id]
        task.actual_hours += hours
        task.updated_at = datetime.now()
        
        # Update project spent hours
        self.projects[project_id].spent_hours += hours
        self.projects[project_id].updated_at = datetime.now()
        
        logger.info(f"Logged {hours} hours to task {task_id}")
    
    def get_project_metrics(self, project_id: str) -> ProjectMetrics:
        """Calculate project metrics."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        project = self.projects[project_id]
        tasks = list(project.tasks.values())
        
        if not tasks:
            return ProjectMetrics(
                project_id=project_id,
                completion_percentage=0.0,
                tasks_completed=0,
                tasks_total=0,
                hours_spent=project.spent_hours,
                hours_estimated=project.budget_hours,
                days_remaining=0,
                is_on_schedule=True,
                blocked_tasks=0,
                overdue_tasks=0
            )
        
        # Calculate metrics
        tasks_completed = len([t for t in tasks if t.status == TaskStatus.COMPLETED])
        tasks_total = len(tasks)
        completion_percentage = (tasks_completed / tasks_total) * 100 if tasks_total > 0 else 0
        
        blocked_tasks = len([t for t in tasks if t.status == TaskStatus.BLOCKED])
        overdue_tasks = len([
            t for t in tasks 
            if t.due_date and t.due_date < datetime.now() and t.status != TaskStatus.COMPLETED
        ])
        
        # Calculate days remaining
        days_remaining = 0
        if project.due_date:
            days_remaining = max(0, (project.due_date - datetime.now()).days)
        
        # Determine if on schedule (simplified logic)
        is_on_schedule = True
        if project.due_date and completion_percentage < 100:
            expected_progress = self._calculate_expected_progress(project)
            is_on_schedule = completion_percentage >= expected_progress * 0.9  # 10% tolerance
        
        return ProjectMetrics(
            project_id=project_id,
            completion_percentage=completion_percentage,
            tasks_completed=tasks_completed,
            tasks_total=tasks_total,
            hours_spent=project.spent_hours,
            hours_estimated=project.budget_hours,
            days_remaining=days_remaining,
            is_on_schedule=is_on_schedule,
            blocked_tasks=blocked_tasks,
            overdue_tasks=overdue_tasks
        )
    
    def get_task_dependencies(self, project_id: str, task_id: str) -> List[ProjectTask]:
        """Get tasks that this task depends on."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        if task_id not in self.projects[project_id].tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.projects[project_id].tasks[task_id]
        dependencies = []
        
        for dep_id in task.dependencies:
            if dep_id in self.projects[project_id].tasks:
                dependencies.append(self.projects[project_id].tasks[dep_id])
        
        return dependencies
    
    def get_available_tasks(self, project_id: str) -> List[ProjectTask]:
        """Get tasks that can be started (no blocking dependencies)."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        project = self.projects[project_id]
        available_tasks = []
        
        for task in project.tasks.values():
            if task.status == TaskStatus.NOT_STARTED:
                # Check if all dependencies are completed
                dependencies_completed = all(
                    project.tasks.get(dep_id, {}).status == TaskStatus.COMPLETED
                    for dep_id in task.dependencies
                    if dep_id in project.tasks
                )
                
                if dependencies_completed:
                    available_tasks.append(task)
        
        return available_tasks
    
    def get_critical_path(self, project_id: str) -> List[ProjectTask]:
        """Calculate critical path for project (simplified)."""
        if project_id not in self.projects:
            raise ValueError(f"Project {project_id} not found")
        
        project = self.projects[project_id]
        tasks = list(project.tasks.values())
        
        # Simplified critical path: longest chain of dependencies
        # In a full implementation, this would use proper CPM algorithm
        critical_tasks = []
        
        # Find tasks with no dependencies (start tasks)
        start_tasks = [t for t in tasks if not t.dependencies]
        
        if start_tasks:
            # For simplicity, take the longest estimated task chain
            longest_chain = []
            max_duration = 0
            
            for start_task in start_tasks:
                chain = self._get_task_chain(project, start_task.id)
                chain_duration = sum(t.estimated_hours for t in chain)
                
                if chain_duration > max_duration:
                    max_duration = chain_duration
                    longest_chain = chain
            
            critical_tasks = longest_chain
        
        return critical_tasks
    
    def get_resource_utilization(self) -> Dict[str, Dict[str, Any]]:
        """Get resource utilization across all projects."""
        utilization = {}
        
        for project in self.projects.values():
            for task in project.tasks.values():
                for agent_id in task.assigned_agents:
                    if agent_id not in utilization:
                        utilization[agent_id] = {
                            'total_hours': 0.0,
                            'projects': [],
                            'tasks': []
                        }
                    
                    utilization[agent_id]['total_hours'] += task.estimated_hours
                    if project.id not in utilization[agent_id]['projects']:
                        utilization[agent_id]['projects'].append(project.id)
                    utilization[agent_id]['tasks'].append({
                        'project_id': project.id,
                        'task_id': task.id,
                        'task_title': task.title,
                        'hours': task.estimated_hours,
                        'status': task.status.value
                    })
        
        return utilization
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data."""
        projects_data = []
        
        for project in self.projects.values():
            metrics = self.get_project_metrics(project.id)
            available_tasks = self.get_available_tasks(project.id)
            critical_path = self.get_critical_path(project.id)
            
            projects_data.append({
                'project': asdict(project),
                'metrics': asdict(metrics),
                'available_tasks': len(available_tasks),
                'critical_path_length': len(critical_path),
                'next_tasks': [asdict(t) for t in available_tasks[:3]]  # Next 3 available tasks
            })
        
        # Overall statistics
        total_projects = len(self.projects)
        active_projects = len([p for p in self.projects.values() if p.status == ProjectStatus.ACTIVE])
        completed_projects = len([p for p in self.projects.values() if p.status == ProjectStatus.COMPLETED])
        
        total_tasks = sum(len(p.tasks) for p in self.projects.values())
        completed_tasks = sum(
            len([t for t in p.tasks.values() if t.status == TaskStatus.COMPLETED])
            for p in self.projects.values()
        )
        
        resource_utilization = self.get_resource_utilization()
        
        return {
            'projects': projects_data,
            'summary': {
                'total_projects': total_projects,
                'active_projects': active_projects,
                'completed_projects': completed_projects,
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
            },
            'resource_utilization': resource_utilization
        }
    
    def _all_tasks_completed(self, project_id: str) -> bool:
        """Check if all tasks in project are completed."""
        project = self.projects[project_id]
        if not project.tasks:
            return False
        
        return all(task.status == TaskStatus.COMPLETED for task in project.tasks.values())
    
    def _calculate_expected_progress(self, project: Project) -> float:
        """Calculate expected progress based on timeline."""
        if not project.start_date or not project.due_date:
            return 0.0
        
        now = datetime.now()
        total_duration = (project.due_date - project.start_date).total_seconds()
        elapsed_duration = (now - project.start_date).total_seconds()
        
        if total_duration <= 0:
            return 100.0
        
        expected_progress = min(100.0, (elapsed_duration / total_duration) * 100)
        return max(0.0, expected_progress)
    
    def _get_task_chain(self, project: Project, task_id: str, visited: set = None) -> List[ProjectTask]:
        """Get chain of dependent tasks (for critical path calculation)."""
        if visited is None:
            visited = set()
        
        if task_id in visited or task_id not in project.tasks:
            return []
        
        visited.add(task_id)
        task = project.tasks[task_id]
        chain = [task]
        
        # Find tasks that depend on this task
        dependent_tasks = [
            t for t in project.tasks.values()
            if task_id in t.dependencies
        ]
        
        # Add the longest dependent chain
        longest_dependent_chain = []
        max_duration = 0
        
        for dep_task in dependent_tasks:
            dep_chain = self._get_task_chain(project, dep_task.id, visited.copy())
            dep_duration = sum(t.estimated_hours for t in dep_chain)
            
            if dep_duration > max_duration:
                max_duration = dep_duration
                longest_dependent_chain = dep_chain
        
        chain.extend(longest_dependent_chain)
        return chain
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'projects': {
                pid: {
                    **asdict(project),
                    'tasks': {tid: asdict(task) for tid, task in project.tasks.items()}
                }
                for pid, project in self.projects.items()
            },
            'resource_allocations': [asdict(ra) for ra in self.resource_allocations]
        }
