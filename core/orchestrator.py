"""
Task Orchestration Engine
Coordinates the execution of tasks using dynamically created agents and tools.
"""

import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

from .groq_model import get_groq_model
from .task_analyzer import TaskAnalysis, TaskComplexity, HITLRequirement
from .dynamic_builder import DynamicBuilder, ToolSpec, AgentSpec

logger = logging.getLogger(__name__)

@dataclass
class ExecutionResult:
    """Result of task execution."""
    task_id: str
    success: bool
    result: Any
    execution_time: float
    agents_used: List[str]
    tools_created: List[str]
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

@dataclass
class SwarmExecution:
    """Tracks a swarm execution."""
    swarm_id: str
    task_id: str
    swarm: Swarm
    start_time: datetime
    status: str  # 'running', 'completed', 'failed'
    result: Optional[Any] = None

class TaskOrchestrator:
    """Orchestrates task execution with dynamic agent and tool creation."""
    
    def __init__(self):
        self.dynamic_builder = DynamicBuilder()
        self.active_swarms: Dict[str, SwarmExecution] = {}
        self.execution_history: List[ExecutionResult] = []
        
    async def execute_task(
        self, 
        task_id: str, 
        task: str, 
        analysis: Dict[str, Any], 
        modifications: Optional[Dict[str, Any]] = None
    ) -> ExecutionResult:
        """Execute a task based on its analysis."""
        logger.info(f"Starting task execution for {task_id}")
        start_time = datetime.now()
        
        try:
            # Parse analysis
            complexity = analysis.get('complexity', 'moderate')
            required_capabilities = analysis.get('required_capabilities', [])
            required_tools = analysis.get('required_tools', [])
            required_agents = analysis.get('required_agents', [])
            subtasks = analysis.get('subtasks', [])
            
            # Apply modifications if provided
            if modifications:
                required_capabilities.extend(modifications.get('additional_capabilities', []))
                required_tools.extend(modifications.get('additional_tools', []))
                required_agents.extend(modifications.get('additional_agents', []))
            
            # Create required tools
            logger.info(f"Creating {len(required_tools)} tools for task {task_id}")
            tools_created = []
            for tool_name in required_tools:
                try:
                    tool_spec = self._create_tool_spec(tool_name, required_capabilities)
                    await self.dynamic_builder.create_tool(tool_spec)
                    tools_created.append(tool_name)
                    logger.info(f"Created tool: {tool_name}")
                except Exception as e:
                    logger.warning(f"Failed to create tool {tool_name}: {e}")
            
            # Create required agents
            logger.info(f"Creating {len(required_agents)} agents for task {task_id}")
            agents_created = []
            for agent_name in required_agents:
                try:
                    agent_spec = self._create_agent_spec(agent_name, required_tools, complexity)
                    await self.dynamic_builder.create_agent(agent_spec)
                    agents_created.append(agent_name)
                    logger.info(f"Created agent: {agent_name}")
                except Exception as e:
                    logger.warning(f"Failed to create agent {agent_name}: {e}")
            
            # Get created agents for swarm
            swarm_agents = []
            for agent_name in agents_created:
                if agent_name in self.dynamic_builder.created_agents:
                    swarm_agents.append(self.dynamic_builder.created_agents[agent_name])
            
            # Fallback: create basic agents if none were created
            if not swarm_agents:
                logger.warning("No agents created, using fallback basic agents")
                swarm_agents = await self._create_fallback_agents(required_capabilities)
            
            # Create and configure swarm
            swarm = self._create_swarm(swarm_agents, complexity)
            
            # Track swarm execution
            swarm_id = str(uuid.uuid4())
            swarm_execution = SwarmExecution(
                swarm_id=swarm_id,
                task_id=task_id,
                swarm=swarm,
                start_time=start_time,
                status='running'
            )
            self.active_swarms[swarm_id] = swarm_execution
            
            # Execute task with swarm
            logger.info(f"Executing task {task_id} with swarm {swarm_id}")
            
            # Prepare enhanced task description with context
            enhanced_task = self._enhance_task_description(task, analysis, subtasks)
            
            # Execute the swarm
            swarm_result = await swarm.invoke_async(enhanced_task)
            
            # Update swarm execution
            swarm_execution.status = 'completed'
            swarm_execution.result = swarm_result
            
            # Calculate execution time
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Create execution result
            result = ExecutionResult(
                task_id=task_id,
                success=True,
                result=swarm_result,
                execution_time=execution_time,
                agents_used=agents_created,
                tools_created=tools_created,
                metadata={
                    'swarm_id': swarm_id,
                    'complexity': complexity,
                    'capabilities_used': required_capabilities,
                    'swarm_status': swarm_result.status.value if hasattr(swarm_result, 'status') else 'unknown'
                }
            )
            
            self.execution_history.append(result)
            logger.info(f"Task {task_id} completed successfully in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Task execution failed for {task_id}: {e}")
            
            # Update swarm execution if it exists
            for swarm_exec in self.active_swarms.values():
                if swarm_exec.task_id == task_id:
                    swarm_exec.status = 'failed'
                    break
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            result = ExecutionResult(
                task_id=task_id,
                success=False,
                result=None,
                execution_time=execution_time,
                agents_used=[],
                tools_created=[],
                error=str(e),
                metadata={'error_type': type(e).__name__}
            )
            
            self.execution_history.append(result)
            return result
    
    def _create_tool_spec(self, tool_name: str, capabilities: List[str]) -> ToolSpec:
        """Create a tool specification based on name and capabilities."""
        tool_templates = {
            'web_search': ToolSpec(
                name='web_search',
                description='Search the web for information on various topics',
                parameters={'query': 'str'},
                implementation='web search with comprehensive results',
                dependencies=['requests', 'beautifulsoup4']
            ),
            'calculate': ToolSpec(
                name='calculate',
                description='Perform mathematical calculations and financial projections',
                parameters={'expression': 'str'},
                implementation='safe mathematical evaluation with financial modeling',
                dependencies=['math']
            ),
            'format_report': ToolSpec(
                name='format_report',
                description='Create professional formatted reports and documents',
                parameters={'title': 'str', 'content': 'str', 'data': 'str'},
                implementation='professional report formatting with analysis',
                dependencies=[]
            ),
            'file_processor': ToolSpec(
                name='file_processor',
                description='Process and analyze various file types',
                parameters={'file_path': 'str', 'operation': 'str'},
                implementation='multi-format file processing',
                dependencies=['pandas', 'openpyxl']
            ),
            'api_client': ToolSpec(
                name='api_client',
                description='Make API calls and handle responses',
                parameters={'url': 'str', 'method': 'str', 'data': 'Optional[Dict]'},
                implementation='robust API client with error handling',
                dependencies=['requests', 'httpx']
            ),
            'data_analyzer': ToolSpec(
                name='data_analyzer',
                description='Analyze and visualize data patterns',
                parameters={'data': 'Any', 'analysis_type': 'str'},
                implementation='comprehensive data analysis',
                dependencies=['pandas', 'numpy', 'matplotlib']
            )
        }
        
        # Return specific template or create custom one
        if tool_name in tool_templates:
            return tool_templates[tool_name]
        
        # Create custom tool based on capabilities
        custom_description = f"Custom {tool_name} tool"
        custom_implementation = "custom functionality"
        
        if 'research' in capabilities:
            custom_description += " for research and information gathering"
            custom_implementation = "research-focused functionality"
        elif 'calculation' in capabilities:
            custom_description += " for calculations and analysis"
            custom_implementation = "calculation and analysis functionality"
        elif 'writing' in capabilities:
            custom_description += " for writing and documentation"
            custom_implementation = "writing and formatting functionality"
        
        return ToolSpec(
            name=tool_name,
            description=custom_description,
            parameters={'input': 'str'},
            implementation=custom_implementation,
            dependencies=[]
        )
    
    def _create_agent_spec(self, agent_name: str, available_tools: List[str], complexity: str) -> AgentSpec:
        """Create an agent specification based on name and context."""
        agent_templates = {
            'researcher': AgentSpec(
                name='researcher',
                description='Expert research agent specializing in information gathering and analysis',
                system_prompt='',  # Will be generated by dynamic builder
                required_tools=['web_search', 'data_analyzer'],
                specialization='research'
            ),
            'analyst': AgentSpec(
                name='analyst',
                description='Quantitative analysis expert specializing in data and financial modeling',
                system_prompt='',
                required_tools=['calculate', 'data_analyzer'],
                specialization='analyst'
            ),
            'writer': AgentSpec(
                name='writer',
                description='Professional writing specialist for reports and documentation',
                system_prompt='',
                required_tools=['format_report', 'file_processor'],
                specialization='writer'
            ),
            'coordinator': AgentSpec(
                name='coordinator',
                description='Task coordination specialist for complex multi-step processes',
                system_prompt='',
                required_tools=['api_client', 'data_analyzer'],
                specialization='coordinator'
            ),
            'specialist': AgentSpec(
                name='specialist',
                description='Domain specialist for complex technical tasks',
                system_prompt='',
                required_tools=available_tools[:3],  # Use first 3 available tools
                specialization='specialist'
            )
        }
        
        if agent_name in agent_templates:
            spec = agent_templates[agent_name]
            # Ensure tools are available
            spec.required_tools = [tool for tool in spec.required_tools if tool in available_tools]
            return spec
        
        # Create custom agent spec
        return AgentSpec(
            name=agent_name,
            description=f'Custom {agent_name} agent for specialized tasks',
            system_prompt='',
            required_tools=available_tools[:2],  # Use first 2 available tools
            specialization=agent_name
        )
    
    async def _create_fallback_agents(self, capabilities: List[str]) -> List:
        """Create basic fallback agents when dynamic creation fails."""
        logger.info("Creating fallback agents")
        
        fallback_agents = []
        
        # Create basic researcher if research capability needed
        if 'research' in capabilities:
            researcher_spec = AgentSpec(
                name='fallback_researcher',
                description='Basic research agent',
                system_prompt='You are a research agent. Gather information and hand off to other agents as needed.',
                required_tools=['web_search'],
                specialization='research'
            )
            agent = await self.dynamic_builder.create_agent(researcher_spec)
            fallback_agents.append(agent)
        
        # Create basic analyst if calculation capability needed
        if 'calculation' in capabilities:
            analyst_spec = AgentSpec(
                name='fallback_analyst',
                description='Basic analysis agent',
                system_prompt='You are an analysis agent. Perform calculations and hand off to other agents as needed.',
                required_tools=['calculate'],
                specialization='analyst'
            )
            agent = await self.dynamic_builder.create_agent(analyst_spec)
            fallback_agents.append(agent)
        
        # Always create a basic writer for output
        writer_spec = AgentSpec(
            name='fallback_writer',
            description='Basic writing agent',
            system_prompt='You are a writing agent. Create formatted output and reports.',
            required_tools=['format_report'],
            specialization='writer'
        )
        agent = await self.dynamic_builder.create_agent(writer_spec)
        fallback_agents.append(agent)
        
        return fallback_agents
    
    def _create_swarm(self, agents: List, complexity: str) -> Swarm:
        """Create a swarm with appropriate configuration based on complexity."""
        # Configure swarm parameters based on complexity
        if complexity == 'simple':
            config = {
                'max_handoffs': 5,
                'max_iterations': 8,
                'execution_timeout': 300.0,  # 5 minutes
                'node_timeout': 60.0  # 1 minute
            }
        elif complexity == 'moderate':
            config = {
                'max_handoffs': 10,
                'max_iterations': 15,
                'execution_timeout': 600.0,  # 10 minutes
                'node_timeout': 120.0  # 2 minutes
            }
        elif complexity == 'complex':
            config = {
                'max_handoffs': 15,
                'max_iterations': 25,
                'execution_timeout': 1200.0,  # 20 minutes
                'node_timeout': 300.0  # 5 minutes
            }
        else:  # expert
            config = {
                'max_handoffs': 25,
                'max_iterations': 40,
                'execution_timeout': 1800.0,  # 30 minutes
                'node_timeout': 600.0  # 10 minutes
            }
        
        # Create swarm with configuration
        swarm = Swarm(
            nodes=agents,
            entry_point=agents[0] if agents else None,
            repetitive_handoff_detection_window=5,
            repetitive_handoff_min_unique_agents=2,
            **config
        )
        
        return swarm
    
    def _enhance_task_description(self, task: str, analysis: Dict[str, Any], subtasks: List[Dict]) -> str:
        """Enhance task description with analysis context and subtasks."""
        enhanced_description = f"""
TASK: {task}

ANALYSIS CONTEXT:
- Complexity: {analysis.get('complexity', 'moderate')}
- Required Capabilities: {', '.join(analysis.get('required_capabilities', []))}
- Estimated Duration: {analysis.get('estimated_duration', 'unknown')} minutes
- Success Criteria: {', '.join(analysis.get('success_criteria', ['task completion']))}

EXECUTION GUIDANCE:
This task has been analyzed and broken down for optimal execution. Work collaboratively with other agents in the swarm, using handoffs when you need specialized capabilities outside your expertise.

Key considerations:
- Focus on quality and accuracy
- Provide detailed context when handing off to other agents
- Ensure all aspects of the task are addressed
- Create comprehensive, actionable output

If you encounter issues or need human input, clearly indicate what type of assistance is needed.
"""
        
        # Add subtask information if available
        if subtasks:
            enhanced_description += "\n\nSUBTASK BREAKDOWN:\n"
            for i, subtask in enumerate(subtasks, 1):
                enhanced_description += f"{i}. {subtask.get('title', 'Subtask')}: {subtask.get('description', 'No description')}\n"
        
        return enhanced_description
    
    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get execution metrics for observability."""
        total_executions = len(self.execution_history)
        successful_executions = len([r for r in self.execution_history if r.success])
        failed_executions = total_executions - successful_executions
        
        if total_executions > 0:
            success_rate = (successful_executions / total_executions) * 100
            avg_execution_time = sum(r.execution_time for r in self.execution_history) / total_executions
        else:
            success_rate = 0
            avg_execution_time = 0
        
        return {
            'total_executions': total_executions,
            'successful_executions': successful_executions,
            'failed_executions': failed_executions,
            'success_rate': success_rate,
            'average_execution_time': avg_execution_time,
            'active_swarms': len([s for s in self.active_swarms.values() if s.status == 'running']),
            'total_agents_created': len(self.dynamic_builder.created_agents),
            'total_tools_created': len(self.dynamic_builder.created_tools)
        }
    
    def get_active_swarms(self) -> List[Dict[str, Any]]:
        """Get information about active swarms."""
        return [
            {
                'swarm_id': swarm.swarm_id,
                'task_id': swarm.task_id,
                'start_time': swarm.start_time.isoformat(),
                'status': swarm.status,
                'duration': (datetime.now() - swarm.start_time).total_seconds()
            }
            for swarm in self.active_swarms.values()
        ]
