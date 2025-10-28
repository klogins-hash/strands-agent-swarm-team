"""
Simple Agent Implementation for Groq API
Minimal multi-agent system without complex dependencies.
"""

import asyncio
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from .groq_model import get_groq_model

logger = logging.getLogger(__name__)

@dataclass
class Message:
    """Simple message structure for agent communication."""
    sender: str
    recipient: str
    content: str
    message_type: str = "text"
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class SimpleAgent:
    """Minimal agent implementation using Groq API."""
    
    def __init__(self, name: str, role: str, system_prompt: str = None):
        self.name = name
        self.role = role
        self.groq_model = get_groq_model()
        self.system_prompt = system_prompt or f"You are {name}, a {role} agent."
        self.message_history: List[Message] = []
        
    async def process_message(self, message: Message) -> str:
        """Process an incoming message and generate a response."""
        try:
            # Add message to history
            self.message_history.append(message)
            
            # Create context from recent messages
            context = self._build_context()
            
            # Generate response using Groq
            prompt = f"""
            Context: {context}
            
            New message from {message.sender}: {message.content}
            
            Respond as {self.name} ({self.role}). Be helpful and concise.
            """
            
            response = await self.groq_model.generate(
                prompt=prompt,
                system_prompt=self.system_prompt,
                max_tokens=1000,
                temperature=0.7
            )
            
            logger.info(f"{self.name} processed message from {message.sender}")
            return response
            
        except Exception as e:
            logger.error(f"Error processing message in {self.name}: {e}")
            return f"Sorry, I encountered an error: {str(e)}"
    
    async def send_message(self, recipient: str, content: str, message_type: str = "text") -> Message:
        """Send a message to another agent."""
        message = Message(
            sender=self.name,
            recipient=recipient,
            content=content,
            message_type=message_type
        )
        
        self.message_history.append(message)
        logger.info(f"{self.name} sent message to {recipient}")
        return message
    
    def _build_context(self, max_messages: int = 5) -> str:
        """Build context from recent message history."""
        recent_messages = self.message_history[-max_messages:]
        context_parts = []
        
        for msg in recent_messages:
            context_parts.append(f"{msg.sender}: {msg.content}")
        
        return "\n".join(context_parts)
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information."""
        return {
            "name": self.name,
            "role": self.role,
            "message_count": len(self.message_history),
            "system_prompt": self.system_prompt
        }

class SimpleSwarm:
    """Minimal multi-agent orchestration system."""
    
    def __init__(self):
        self.agents: Dict[str, SimpleAgent] = {}
        self.message_queue: List[Message] = []
        
    def add_agent(self, agent: SimpleAgent):
        """Add an agent to the swarm."""
        self.agents[agent.name] = agent
        logger.info(f"Added agent {agent.name} to swarm")
    
    def create_agent(self, name: str, role: str, system_prompt: str = None) -> SimpleAgent:
        """Create and add a new agent to the swarm."""
        agent = SimpleAgent(name, role, system_prompt)
        self.add_agent(agent)
        return agent
    
    async def route_message(self, message: Message) -> str:
        """Route a message to the appropriate agent."""
        if message.recipient not in self.agents:
            return f"Agent {message.recipient} not found in swarm"
        
        recipient_agent = self.agents[message.recipient]
        response = await recipient_agent.process_message(message)
        return response
    
    async def broadcast_message(self, sender: str, content: str) -> Dict[str, str]:
        """Broadcast a message to all agents except sender."""
        responses = {}
        
        for agent_name, agent in self.agents.items():
            if agent_name != sender:
                message = Message(sender=sender, recipient=agent_name, content=content)
                response = await agent.process_message(message)
                responses[agent_name] = response
        
        return responses
    
    async def execute_task(self, task: str, coordinator: str = None) -> Dict[str, Any]:
        """Execute a task using the agent swarm."""
        if not self.agents:
            return {"error": "No agents available in swarm"}
        
        # Use first agent as coordinator if none specified
        if not coordinator:
            coordinator = list(self.agents.keys())[0]
        
        if coordinator not in self.agents:
            return {"error": f"Coordinator {coordinator} not found"}
        
        # Send task to coordinator
        task_message = Message(
            sender="system",
            recipient=coordinator,
            content=f"Task: {task}",
            message_type="task"
        )
        
        coordinator_response = await self.route_message(task_message)
        
        # Collect responses from all agents
        all_responses = await self.broadcast_message("system", f"Collaborate on task: {task}")
        all_responses[coordinator] = coordinator_response
        
        return {
            "task": task,
            "coordinator": coordinator,
            "responses": all_responses,
            "status": "completed"
        }
    
    def get_swarm_info(self) -> Dict[str, Any]:
        """Get information about the swarm."""
        return {
            "agent_count": len(self.agents),
            "agents": {name: agent.get_info() for name, agent in self.agents.items()},
            "total_messages": sum(len(agent.message_history) for agent in self.agents.values())
        }

# Pre-configured agent templates
class AgentTemplates:
    """Pre-configured agent templates for common roles."""
    
    @staticmethod
    def create_researcher(name: str = "researcher") -> SimpleAgent:
        """Create a research specialist agent."""
        system_prompt = """
        You are a research specialist agent. Your role is to:
        - Gather and analyze information
        - Provide factual, well-sourced responses
        - Break down complex research tasks
        - Collaborate with other agents when needed
        
        Always be thorough and cite your reasoning.
        """
        return SimpleAgent(name, "researcher", system_prompt)
    
    @staticmethod
    def create_analyst(name: str = "analyst") -> SimpleAgent:
        """Create a data analysis specialist agent."""
        system_prompt = """
        You are a data analysis specialist agent. Your role is to:
        - Analyze data and identify patterns
        - Perform calculations and statistical analysis
        - Create summaries and insights
        - Work with other agents to solve complex problems
        
        Always show your work and explain your reasoning.
        """
        return SimpleAgent(name, "analyst", system_prompt)
    
    @staticmethod
    def create_writer(name: str = "writer") -> SimpleAgent:
        """Create a writing specialist agent."""
        system_prompt = """
        You are a writing specialist agent. Your role is to:
        - Create clear, professional documents
        - Synthesize information from multiple sources
        - Format reports and presentations
        - Ensure consistency and quality in written output
        
        Always write clearly and professionally.
        """
        return SimpleAgent(name, "writer", system_prompt)
    
    @staticmethod
    def create_coordinator(name: str = "coordinator") -> SimpleAgent:
        """Create a task coordination specialist agent."""
        system_prompt = """
        You are a task coordination specialist agent. Your role is to:
        - Break down complex tasks into subtasks
        - Coordinate between different specialist agents
        - Monitor progress and ensure quality
        - Make decisions about task routing and prioritization
        
        Always think strategically and coordinate effectively.
        """
        return SimpleAgent(name, "coordinator", system_prompt)

# Factory function for creating common swarm configurations
def create_basic_swarm() -> SimpleSwarm:
    """Create a basic swarm with common agent types."""
    swarm = SimpleSwarm()
    
    # Add standard agents
    swarm.add_agent(AgentTemplates.create_researcher())
    swarm.add_agent(AgentTemplates.create_analyst())
    swarm.add_agent(AgentTemplates.create_writer())
    swarm.add_agent(AgentTemplates.create_coordinator())
    
    logger.info("Created basic swarm with 4 agents")
    return swarm
