"""
Dynamic Agent and Tool Builder
Creates agents and tools on-demand based on task requirements.
"""

import json
import logging
import inspect
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from .groq_model import get_groq_model
import importlib.util
import tempfile
import os

logger = logging.getLogger(__name__)

@dataclass
class ToolSpec:
    """Specification for a tool to be created."""
    name: str
    description: str
    parameters: Dict[str, Any]
    implementation: str
    dependencies: List[str]

@dataclass
class AgentSpec:
    """Specification for an agent to be created."""
    name: str
    description: str
    system_prompt: str
    required_tools: List[str]
    specialization: str

class DynamicBuilder:
    """Builds agents and tools dynamically based on requirements."""
    
    def __init__(self, model=None):
        self.groq_model = get_groq_model()
        self.builder_agent = self._create_builder_agent()
        self.created_tools = {}
        self.created_agents = {}
        
    def _create_builder_agent(self):
        """Create the dynamic builder agent."""
        
        def generate_tool_code(tool_name: str, description: str, requirements: str) -> str:
            """Generate Python code for a custom tool."""
            # Template for tool generation
            tool_template = f'''
def {tool_name}({{parameters}}) -> str:
    """{{description}}"""
    try:
        # Implementation based on requirements
        {{implementation}}
        return f"{{tool_name}} executed successfully: {{result}}"
    except Exception as e:
        return f"Error in {{tool_name}}: {{str(e)}}"
'''
            
            # Common tool implementations based on requirements
            implementations = {
                "web_scraping": '''
        import requests
        from bs4 import BeautifulSoup
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        result = soup.get_text()[:500]  # First 500 chars
        ''',
                "file_processing": '''
        import os
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            result = f"Processed file: {len(content)} characters"
        else:
            result = "File not found"
        ''',
                "api_call": '''
        import requests
        response = requests.get(api_url, headers=headers or {})
        result = response.json() if response.status_code == 200 else "API call failed"
        ''',
                "data_processing": '''
        import json
        if isinstance(data, str):
            try:
                parsed_data = json.loads(data)
                result = f"Processed {len(parsed_data)} items"
            except:
                result = f"Processed text data: {len(data)} characters"
        else:
            result = f"Processed data: {type(data)}"
        '''
            }
            
            # Determine implementation based on requirements
            req_lower = requirements.lower()
            implementation = "result = 'Basic implementation'"
            
            if "web" in req_lower or "scrape" in req_lower:
                implementation = implementations["web_scraping"]
            elif "file" in req_lower:
                implementation = implementations["file_processing"] 
            elif "api" in req_lower:
                implementation = implementations["api_call"]
            elif "data" in req_lower:
                implementation = implementations["data_processing"]
            
            return json.dumps({
                "tool_code": tool_template,
                "implementation": implementation,
                "suggested_parameters": self._suggest_parameters(requirements)
            })
        
        def generate_agent_prompt(agent_name: str, specialization: str, tools: str) -> str:
            """Generate system prompt for a specialized agent."""
            prompt_templates = {
                "researcher": f"""
You are {agent_name}, a specialized research agent. Your expertise includes:
- Information gathering and analysis
- Web research and data collection
- Fact verification and source validation

Your available tools: {tools}

When working on tasks:
1. Gather comprehensive information first
2. Verify sources and data quality
3. Hand off to appropriate specialists when needed
4. Always provide detailed context in handoffs
""",
                "analyst": f"""
You are {agent_name}, a specialized data analysis agent. Your expertise includes:
- Quantitative analysis and modeling
- Statistical analysis and projections
- Data interpretation and insights

Your available tools: {tools}

When working on tasks:
1. Perform thorough analysis of provided data
2. Create models and projections as needed
3. Validate results and assumptions
4. Hand off to appropriate specialists for next steps
""",
                "writer": f"""
You are {agent_name}, a specialized writing and documentation agent. Your expertise includes:
- Professional document creation
- Report formatting and presentation
- Content synthesis and organization

Your available tools: {tools}

When working on tasks:
1. Synthesize information from multiple sources
2. Create well-structured, professional documents
3. Ensure clarity and actionable recommendations
4. Request additional information if needed
""",
                "coordinator": f"""
You are {agent_name}, a task coordination and planning agent. Your expertise includes:
- Task breakdown and planning
- Agent coordination and workflow management
- Progress tracking and quality assurance

Your available tools: {tools}

When working on tasks:
1. Break down complex tasks into manageable steps
2. Coordinate between different specialist agents
3. Monitor progress and ensure quality
4. Escalate to humans when required
"""
            }
            
            # Use template based on specialization or create custom
            if specialization.lower() in prompt_templates:
                prompt = prompt_templates[specialization.lower()]
            else:
                prompt = f"""
You are {agent_name}, a specialized agent focused on {specialization}.

Your available tools: {tools}

Your role is to handle tasks related to {specialization} with expertise and precision.
Always coordinate with other agents when your task requires capabilities outside your specialization.
"""
            
            return json.dumps({
                "system_prompt": prompt,
                "specialization": specialization,
                "coordination_strategy": "Hand off to appropriate specialists when needed"
            })
        
        # Create a simple agent-like class for Groq
        class GroqDynamicBuilder:
            def __init__(self, groq_model):
                self.groq_model = groq_model
                self.system_prompt = (
                    "You are an expert system architect that creates agents and tools dynamically. "
                    "When given requirements, you generate appropriate code and configurations. "
                    "Always consider best practices, error handling, and integration with existing systems. "
                    "Focus on creating practical, working solutions that integrate well with the existing system."
                )
            
            async def invoke_async(self, prompt):
                return await self.groq_model.generate(
                    prompt=prompt,
                    system_prompt=self.system_prompt,
                    max_tokens=2000,
                    temperature=0.2
                )
        
        return GroqDynamicBuilder(self.groq_model)
    
    def _suggest_parameters(self, requirements: str) -> Dict[str, str]:
        """Suggest parameters for a tool based on requirements."""
        req_lower = requirements.lower()
        
        if "web" in req_lower or "url" in req_lower:
            return {"url": "str", "headers": "Optional[Dict[str, str]] = None"}
        elif "file" in req_lower:
            return {"file_path": "str", "encoding": "str = 'utf-8'"}
        elif "api" in req_lower:
            return {"api_url": "str", "headers": "Optional[Dict[str, str]] = None", "params": "Optional[Dict[str, Any]] = None"}
        elif "data" in req_lower:
            return {"data": "Any", "format": "str = 'json'"}
        else:
            return {"input_data": "str"}
    
    async def create_tool(self, tool_spec: ToolSpec) -> Callable:
        """Create a tool dynamically based on specification."""
        logger.info(f"Creating tool: {tool_spec.name}")
        
        try:
            # Generate tool code using the builder agent
            prompt = f"""
            Create a tool with these specifications:
            Name: {tool_spec.name}
            Description: {tool_spec.description}
            Requirements: {tool_spec.implementation}
            
            Generate the complete Python code for this tool.
            """
            
            result = await self.builder_agent.invoke_async(prompt)
            
            # For now, create a basic tool implementation
            # In a full implementation, you'd parse the generated code and create the actual tool
            def dynamic_tool(*args, **kwargs) -> str:
                return f"Dynamic tool {tool_spec.name} executed with args: {args}, kwargs: {kwargs}"
            
            # Add tool decorator
            dynamic_tool = tool(dynamic_tool)
            dynamic_tool.__name__ = tool_spec.name
            dynamic_tool.__doc__ = tool_spec.description
            
            self.created_tools[tool_spec.name] = dynamic_tool
            logger.info(f"Successfully created tool: {tool_spec.name}")
            
            return dynamic_tool
            
        except Exception as e:
            logger.error(f"Error creating tool {tool_spec.name}: {e}")
            raise
    
    async def create_agent(self, agent_spec: AgentSpec):
        """Create an agent dynamically based on specification."""
        logger.info(f"Creating agent: {agent_spec.name}")
        
        try:
            # Generate system prompt using the builder agent
            tools_str = ", ".join(agent_spec.required_tools)
            prompt = f"""
            Create a system prompt for an agent with these specifications:
            Name: {agent_spec.name}
            Specialization: {agent_spec.specialization}
            Description: {agent_spec.description}
            Available Tools: {tools_str}
            
            Generate a comprehensive system prompt that defines the agent's role and behavior.
            """
            
            result = await self.builder_agent.invoke_async(prompt)
            
            # Get required tools (create them if they don't exist)
            agent_tools = []
            for tool_name in agent_spec.required_tools:
                if tool_name in self.created_tools:
                    agent_tools.append(self.created_tools[tool_name])
                else:
                    # Create basic tool if it doesn't exist
                    basic_tool_spec = ToolSpec(
                        name=tool_name,
                        description=f"Basic {tool_name} tool",
                        parameters={},
                        implementation="basic functionality",
                        dependencies=[]
                    )
                    tool_func = await self.create_tool(basic_tool_spec)
                    agent_tools.append(tool_func)
            
            # Create a simple agent-like class for Groq
            class GroqAgent:
                def __init__(self, name, system_prompt, tools, groq_model):
                    self.name = name
                    self.system_prompt = system_prompt
                    self.tools = tools
                    self.groq_model = groq_model
                
                async def invoke_async(self, prompt):
                    return await self.groq_model.generate(
                        prompt=prompt,
                        system_prompt=self.system_prompt,
                        max_tokens=2000,
                        temperature=0.7
                    )
            
            agent = GroqAgent(
                name=agent_spec.name,
                system_prompt=agent_spec.system_prompt or f"You are {agent_spec.name}, specialized in {agent_spec.specialization}.",
                tools=agent_tools,
                groq_model=self.groq_model
            )
            
            self.created_agents[agent_spec.name] = agent
            logger.info(f"Successfully created agent: {agent_spec.name}")
            
            return agent
            
        except Exception as e:
            logger.error(f"Error creating agent {agent_spec.name}: {e}")
            raise
    
    async def create_required_tools(self, required_tools: List[str]) -> List[Callable]:
        """Create all required tools for a task."""
        tools = []
        
        for tool_name in required_tools:
            if tool_name not in self.created_tools:
                # Create tool specification based on name
                tool_spec = self._infer_tool_spec(tool_name)
                tool_func = await self.create_tool(tool_spec)
                tools.append(tool_func)
            else:
                tools.append(self.created_tools[tool_name])
        
        return tools
    
    async def create_required_agents(self, required_agents: List[str], required_tools: List[str]):
        """Create all required agents for a task."""
        agents = []
        
        for agent_name in required_agents:
            if agent_name not in self.created_agents:
                # Create agent specification based on name
                agent_spec = self._infer_agent_spec(agent_name, required_tools)
                agent = await self.create_agent(agent_spec)
                agents.append(agent)
            else:
                agents.append(self.created_agents[agent_name])
        
        return agents
    
    def _infer_tool_spec(self, tool_name: str) -> ToolSpec:
        """Infer tool specification from tool name."""
        tool_specs = {
            "web_search": ToolSpec(
                name="web_search",
                description="Search the web for information",
                parameters={"query": "str"},
                implementation="web search functionality",
                dependencies=["requests"]
            ),
            "calculate": ToolSpec(
                name="calculate", 
                description="Perform mathematical calculations",
                parameters={"expression": "str"},
                implementation="mathematical computation",
                dependencies=[]
            ),
            "format_report": ToolSpec(
                name="format_report",
                description="Format data into professional reports",
                parameters={"title": "str", "content": "str"},
                implementation="report formatting",
                dependencies=[]
            ),
            "file_processor": ToolSpec(
                name="file_processor",
                description="Process various file types",
                parameters={"file_path": "str"},
                implementation="file processing",
                dependencies=["os"]
            )
        }
        
        return tool_specs.get(tool_name, ToolSpec(
            name=tool_name,
            description=f"Custom {tool_name} tool",
            parameters={"input": "str"},
            implementation="custom functionality",
            dependencies=[]
        ))
    
    def _infer_agent_spec(self, agent_name: str, available_tools: List[str]) -> AgentSpec:
        """Infer agent specification from agent name."""
        agent_specs = {
            "researcher": AgentSpec(
                name="researcher",
                description="Research and information gathering specialist",
                system_prompt="",  # Will be generated
                required_tools=["web_search"],
                specialization="research"
            ),
            "analyst": AgentSpec(
                name="analyst",
                description="Data analysis and calculation specialist", 
                system_prompt="",
                required_tools=["calculate"],
                specialization="analyst"
            ),
            "writer": AgentSpec(
                name="writer",
                description="Writing and documentation specialist",
                system_prompt="",
                required_tools=["format_report"],
                specialization="writer"
            ),
            "coordinator": AgentSpec(
                name="coordinator",
                description="Task coordination and planning specialist",
                system_prompt="",
                required_tools=["task_planning"],
                specialization="coordinator"
            )
        }
        
        return agent_specs.get(agent_name, AgentSpec(
            name=agent_name,
            description=f"Custom {agent_name} specialist",
            system_prompt="",
            required_tools=available_tools[:2],  # Use first 2 available tools
            specialization=agent_name
        ))
