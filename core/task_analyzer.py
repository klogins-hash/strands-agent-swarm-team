"""
Autonomous Task Analysis System
Analyzes incoming tasks to determine complexity, HITL requirements, and execution strategy.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
from .groq_model import get_groq_model

logger = logging.getLogger(__name__)

class TaskComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"

class HITLRequirement(Enum):
    NONE = "none"
    APPROVAL = "approval"
    FEEDBACK = "feedback"
    COLLABORATION = "collaboration"
    SUPERVISION = "supervision"

@dataclass
class TaskAnalysis:
    """Complete analysis of a task."""
    task_id: str
    original_task: str
    complexity: TaskComplexity
    hitl_requirement: HITLRequirement
    estimated_duration: int  # minutes
    required_capabilities: List[str]
    subtasks: List[Dict[str, Any]]
    required_tools: List[str]
    required_agents: List[str]
    risk_factors: List[str]
    success_criteria: List[str]
    human_checkpoints: List[str]
    confidence_score: float

@dataclass
class SubTask:
    """Individual subtask definition."""
    id: str
    title: str
    description: str
    dependencies: List[str]
    required_agent: str
    required_tools: List[str]
    estimated_duration: int
    hitl_required: bool
    success_criteria: str

class TaskAnalyzer:
    """Autonomous task analysis system."""
    
    def __init__(self):
        # Initialize with Groq model
        self.groq_model = get_groq_model()
        self.analyzer_agent = self._create_analyzer_agent()
        
    def _create_analyzer_agent(self):
        """Create the task analysis agent."""
        
        def analyze_task_complexity(task: str) -> str:
            """Analyze task complexity and requirements."""
            # Define complexity indicators
            complexity_indicators = {
                "simple": ["single step", "basic", "straightforward", "simple"],
                "moderate": ["multiple steps", "some planning", "coordination"],
                "complex": ["multi-phase", "complex logic", "integration", "analysis"],
                "expert": ["research", "specialized knowledge", "critical decisions"]
            }
            
            task_lower = task.lower()
            complexity_scores = {}
            
            for level, indicators in complexity_indicators.items():
                score = sum(1 for indicator in indicators if indicator in task_lower)
                complexity_scores[level] = score
            
            # Determine complexity
            max_score = max(complexity_scores.values())
            if max_score == 0:
                complexity = "moderate"
            else:
                complexity = max(complexity_scores, key=complexity_scores.get)
            
            return json.dumps({
                "complexity": complexity,
                "indicators_found": complexity_scores,
                "reasoning": f"Task classified as {complexity} based on keyword analysis"
            })
        
        def identify_required_capabilities(task: str) -> str:
            """Identify what capabilities are needed for the task."""
            capability_keywords = {
                "research": ["research", "find", "investigate", "analyze", "study"],
                "calculation": ["calculate", "compute", "math", "financial", "projection"],
                "writing": ["write", "report", "document", "format", "create"],
                "web_scraping": ["scrape", "extract", "website", "web data"],
                "file_processing": ["file", "document", "pdf", "csv", "excel"],
                "api_integration": ["api", "integration", "connect", "fetch"],
                "data_analysis": ["analyze", "data", "statistics", "trends"],
                "automation": ["automate", "schedule", "monitor", "trigger"],
                "communication": ["email", "message", "notify", "alert"],
                "visualization": ["chart", "graph", "plot", "visualize"]
            }
            
            task_lower = task.lower()
            required_capabilities = []
            
            for capability, keywords in capability_keywords.items():
                if any(keyword in task_lower for keyword in keywords):
                    required_capabilities.append(capability)
            
            return json.dumps({
                "required_capabilities": required_capabilities,
                "reasoning": "Identified based on keyword matching and task context"
            })
        
        def determine_hitl_requirements(task: str, complexity: str) -> str:
            """Determine human-in-the-loop requirements."""
            hitl_indicators = {
                "none": ["simple", "routine", "automated"],
                "approval": ["deploy", "publish", "send", "delete", "modify"],
                "feedback": ["creative", "subjective", "opinion", "preference"],
                "collaboration": ["complex", "multi-step", "strategic"],
                "supervision": ["critical", "sensitive", "important", "risky"]
            }
            
            task_lower = task.lower()
            hitl_scores = {}
            
            for level, indicators in hitl_indicators.items():
                score = sum(1 for indicator in indicators if indicator in task_lower)
                if complexity in indicators:
                    score += 2
                hitl_scores[level] = score
            
            # Determine HITL requirement
            max_score = max(hitl_scores.values())
            if max_score == 0:
                hitl_requirement = "approval"
            else:
                hitl_requirement = max(hitl_scores, key=hitl_scores.get)
            
            return json.dumps({
                "hitl_requirement": hitl_requirement,
                "reasoning": f"Based on task content and complexity level: {complexity}",
                "scores": hitl_scores
            })
        
        def break_down_task(task: str, capabilities: str) -> str:
            """Break down task into subtasks."""
            # Parse capabilities
            try:
                caps_data = json.loads(capabilities)
                required_caps = caps_data.get("required_capabilities", [])
            except:
                required_caps = []
            
            # Create subtasks based on capabilities
            subtasks = []
            
            if "research" in required_caps:
                subtasks.append({
                    "id": "research_phase",
                    "title": "Research and Information Gathering",
                    "description": "Gather relevant information and data for the task",
                    "required_agent": "researcher",
                    "required_tools": ["web_search", "data_collection"],
                    "estimated_duration": 15
                })
            
            if "calculation" in required_caps:
                subtasks.append({
                    "id": "analysis_phase", 
                    "title": "Data Analysis and Calculations",
                    "description": "Perform necessary calculations and data analysis",
                    "required_agent": "analyst",
                    "required_tools": ["calculate", "data_analysis"],
                    "estimated_duration": 10
                })
            
            if "writing" in required_caps:
                subtasks.append({
                    "id": "documentation_phase",
                    "title": "Documentation and Reporting",
                    "description": "Create final documentation and reports",
                    "required_agent": "writer",
                    "required_tools": ["format_report", "document_creation"],
                    "estimated_duration": 20
                })
            
            # Add coordination subtask for complex tasks
            if len(subtasks) > 1:
                subtasks.insert(0, {
                    "id": "planning_phase",
                    "title": "Task Planning and Coordination",
                    "description": "Plan task execution and coordinate between agents",
                    "required_agent": "coordinator",
                    "required_tools": ["task_planning", "agent_coordination"],
                    "estimated_duration": 5
                })
            
            return json.dumps({
                "subtasks": subtasks,
                "total_estimated_duration": sum(st["estimated_duration"] for st in subtasks)
            })
        
        # Create a simple agent-like class for Groq
        class GroqTaskAnalyzer:
            def __init__(self, groq_model):
                self.groq_model = groq_model
                self.system_prompt = (
                    "You are an expert task analysis agent. Your role is to thoroughly analyze "
                    "incoming tasks and provide comprehensive breakdowns. Analyze the task for:\n"
                    "1. Complexity level (simple, moderate, complex, expert)\n"
                    "2. Required capabilities (research, analysis, writing, calculation, etc.)\n"
                    "3. Human-in-the-loop requirements (none, approval, supervision, collaboration)\n"
                    "4. Subtask breakdown with dependencies\n"
                    "Always provide detailed reasoning and be thorough in your analysis."
                )
            
            async def invoke_async(self, prompt):
                return await self.groq_model.generate(
                    prompt=prompt,
                    system_prompt=self.system_prompt,
                    max_tokens=2000,
                    temperature=0.3
                )
        
        return GroqTaskAnalyzer(self.groq_model)
    
    async def analyze_task(self, task: str, task_id: str) -> TaskAnalysis:
        """Perform comprehensive task analysis."""
        logger.info(f"Analyzing task {task_id}: {task[:100]}...")
        
        try:
            # Get analysis from the agent
            analysis_prompt = f"""
            Analyze this task comprehensively:
            
            Task: {task}
            
            Please:
            1. First analyze the task complexity
            2. Then identify required capabilities
            3. Determine HITL requirements based on complexity
            4. Finally break down into subtasks
            
            Provide a complete analysis with reasoning for each step.
            """
            
            result = await self.analyzer_agent.invoke_async(analysis_prompt)
            
            # Parse the agent's response to extract structured data
            # This is a simplified version - in practice, you'd parse the actual tool outputs
            analysis = TaskAnalysis(
                task_id=task_id,
                original_task=task,
                complexity=TaskComplexity.MODERATE,  # Default, would be parsed from tool output
                hitl_requirement=HITLRequirement.APPROVAL,  # Default, would be parsed
                estimated_duration=30,  # Default, would be calculated
                required_capabilities=["research", "analysis", "writing"],  # Would be parsed
                subtasks=[],  # Would be populated from tool output
                required_tools=["web_search", "calculate", "format_report"],
                required_agents=["researcher", "analyst", "writer"],
                risk_factors=["complexity", "time_constraints"],
                success_criteria=["task_completion", "quality_output"],
                human_checkpoints=["final_approval"],
                confidence_score=0.85
            )
            
            logger.info(f"Task analysis completed for {task_id}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing task {task_id}: {e}")
            # Return a basic analysis as fallback
            return TaskAnalysis(
                task_id=task_id,
                original_task=task,
                complexity=TaskComplexity.MODERATE,
                hitl_requirement=HITLRequirement.APPROVAL,
                estimated_duration=30,
                required_capabilities=["general"],
                subtasks=[],
                required_tools=["basic_tools"],
                required_agents=["general_agent"],
                risk_factors=["unknown"],
                success_criteria=["completion"],
                human_checkpoints=["approval"],
                confidence_score=0.5
            )
    
    def to_dict(self, analysis: TaskAnalysis) -> Dict[str, Any]:
        """Convert TaskAnalysis to dictionary."""
        data = asdict(analysis)
        # Convert enums to strings
        data['complexity'] = analysis.complexity.value
        data['hitl_requirement'] = analysis.hitl_requirement.value
        return data
