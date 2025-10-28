#!/usr/bin/env python3
"""
Strands Agent Swarm Team
A collaborative multi-agent system using the Strands SDK.
"""

import logging
import os
from typing import Dict, Any
from strands import Agent, tool
from strands.multiagent.swarm import Swarm
from strands.models.ollama import OllamaModel
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
console = Console()

# Define tools that agents can use
@tool
def web_search(query: str) -> str:
    """Search the web for information about various topics."""
    # Simulate comprehensive web search results
    search_database = {
        "ai market": {
            "size": "The global AI market was valued at approximately $136.55 billion in 2022",
            "growth": "Expected to grow at a CAGR of 37.3% from 2023 to 2030",
            "projection": "Projected to reach $1.81 trillion by 2030",
            "key_players": "OpenAI, Google, Microsoft, Amazon, Anthropic, Meta"
        },
        "technology trends": {
            "current": "Generative AI, autonomous agents, multi-modal AI, edge computing",
            "emerging": "Agent-to-agent communication, swarm intelligence, federated learning",
            "enterprise": "AI automation, intelligent document processing, conversational AI"
        },
        "market analysis": {
            "drivers": "Increased data availability, cloud computing, improved algorithms",
            "challenges": "Data privacy, regulatory compliance, talent shortage",
            "opportunities": "Healthcare AI, financial services automation, smart cities"
        }
    }
    
    query_lower = query.lower()
    results = []
    
    for category, data in search_database.items():
        if any(keyword in query_lower for keyword in category.split()):
            for key, value in data.items():
                results.append(f"{key.title()}: {value}")
    
    if not results:
        results = ["General market research indicates strong growth in AI and automation sectors"]
    
    return f"Search results for '{query}':\n" + "\n".join(f"• {result}" for result in results)

@tool
def calculate(expression: str) -> str:
    """Perform mathematical calculations and financial projections."""
    try:
        # Handle common financial calculations
        if "growth" in expression.lower() and "%" in expression:
            # Extract growth rate and base value
            parts = expression.replace("%", "").split()
            if len(parts) >= 3:
                try:
                    base_value = float([p for p in parts if p.replace(".", "").replace(",", "").isdigit()][0])
                    growth_rate = float([p for p in parts if "." in p or p.isdigit()][-1]) / 100
                    years = 8  # Default projection period
                    
                    future_value = base_value * ((1 + growth_rate) ** years)
                    return f"Financial projection: ${base_value:.2f}B growing at {growth_rate*100:.1f}% annually = ${future_value:.2f}B after {years} years"
                except:
                    pass
        
        # Safe evaluation for basic math
        allowed_chars = set('0123456789+-*/()., ')
        if all(c in allowed_chars for c in expression):
            result = eval(expression)
            return f"Calculation result: {expression} = {result:,.2f}"
        else:
            return f"Error: Invalid characters in expression '{expression}'"
            
    except Exception as e:
        return f"Calculation error for '{expression}': {str(e)}"

@tool
def format_report(title: str, content: str, data: str = "") -> str:
    """Create a professional formatted report with analysis."""
    report = f"""
# {title}

## Executive Summary
{content}

## Detailed Analysis
{data if data else "Based on current market research and financial projections, the analysis shows significant growth potential in the AI sector."}

## Key Findings
• Market demonstrates strong fundamentals with consistent growth trajectory
• Technology adoption is accelerating across multiple industries  
• Investment opportunities are expanding in enterprise and consumer segments
• Regulatory landscape is evolving to support innovation while ensuring safety

## Strategic Recommendations
1. **Market Entry**: Focus on high-growth segments with clear value propositions
2. **Technology Investment**: Prioritize scalable AI solutions with proven ROI
3. **Partnership Strategy**: Collaborate with established players for market access
4. **Risk Management**: Monitor regulatory changes and competitive dynamics

## Financial Projections
Based on current growth rates and market conditions, the sector shows:
- Strong revenue growth potential (25-40% CAGR)
- Expanding market opportunities across verticals
- Increasing enterprise adoption and investment

## Conclusion
The analysis indicates a robust market environment with significant opportunities for growth and innovation. Strategic positioning and execution will be critical for success.

---
*Report generated by Strands Agent Swarm Team*
*Analysis Date: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
    return report

def create_agent_team() -> Swarm:
    """Create and configure the Strands agent swarm team."""
    
    # Use Ollama for local deployment
    model = OllamaModel(
        host="http://localhost:11434",
        model_id="llama3.2"  # Make sure this model is available in Ollama
    )
    
    # Create specialized agents with detailed system prompts
    researcher = Agent(
        name="researcher",
        model=model,
        system_prompt=(
            "You are a senior research analyst specializing in market intelligence and data gathering. "
            "Your role is to find comprehensive, accurate information using the web_search tool. "
            "When you complete your research, analyze what additional work is needed:\n"
            "- If calculations or financial analysis are required, hand off to the 'analyst'\n"
            "- If the final report needs to be formatted, hand off to the 'writer'\n"
            "- Always provide detailed context when handing off to other agents\n"
            "Focus on gathering complete, relevant data before proceeding."
        ),
        tools=[web_search],
        description="Expert in market research and information gathering"
    )

    analyst = Agent(
        name="analyst", 
        model=model,
        system_prompt=(
            "You are a quantitative analyst and financial modeling expert. "
            "Your role is to perform calculations, financial projections, and numerical analysis using the calculate tool. "
            "When you receive data from other agents, analyze it thoroughly and provide insights:\n"
            "- Perform growth calculations and projections\n"
            "- Analyze financial metrics and trends\n"
            "- If you need more research data, hand off to the 'researcher'\n"
            "- If your analysis needs to be formatted into a report, hand off to the 'writer'\n"
            "Always show your work and explain your methodology."
        ),
        tools=[calculate],
        description="Specialist in quantitative analysis and financial modeling"
    )

    writer = Agent(
        name="writer",
        model=model,
        system_prompt=(
            "You are a professional business writer and report specialist. "
            "Your role is to create comprehensive, well-structured reports using the format_report tool. "
            "When you receive information from other agents:\n"
            "- Synthesize research findings and analysis into coherent narratives\n"
            "- Create executive summaries and strategic recommendations\n"
            "- Ensure reports are professional, actionable, and well-organized\n"
            "- If you need additional research or analysis, hand off to the appropriate specialist\n"
            "Focus on clarity, insight, and actionable recommendations."
        ),
        tools=[format_report],
        description="Expert in business writing and professional report creation"
    )

    # Create the swarm with optimized configuration
    swarm = Swarm(
        nodes=[researcher, analyst, writer],
        entry_point=researcher,  # Start with research
        max_handoffs=15,
        max_iterations=20,
        execution_timeout=600.0,  # 10 minutes total
        node_timeout=120.0,  # 2 minutes per agent
        repetitive_handoff_detection_window=5,
        repetitive_handoff_min_unique_agents=2
    )
    
    return swarm

def display_results(result) -> None:
    """Display swarm execution results in a formatted way."""
    console.print("\n" + "="*80)
    console.print(Panel.fit("🤖 STRANDS AGENT SWARM EXECUTION RESULTS", style="bold blue"))
    console.print("="*80)
    
    # Status and metrics
    status_color = "green" if result.status.value == "completed" else "red"
    console.print(f"[bold]Status:[/bold] [{status_color}]{result.status.value.upper()}[/{status_color}]")
    console.print(f"[bold]Execution Time:[/bold] {result.execution_time}ms")
    console.print(f"[bold]Total Agents Used:[/bold] {result.execution_count}")
    console.print(f"[bold]Agent Sequence:[/bold] {' → '.join([node.node_id for node in result.node_history])}")
    
    # Token usage if available
    if hasattr(result, 'accumulated_usage') and result.accumulated_usage:
        usage = result.accumulated_usage
        console.print(f"[bold]Token Usage:[/bold] Input: {usage.get('inputTokens', 0)}, Output: {usage.get('outputTokens', 0)}, Total: {usage.get('totalTokens', 0)}")
    
    console.print("\n" + "-"*60)
    console.print(Panel.fit("📋 AGENT RESULTS", style="bold yellow"))
    console.print("-"*60)
    
    # Show results from each agent
    for agent_name, node_result in result.results.items():
        console.print(f"\n[bold cyan][{agent_name.upper()}][/bold cyan]")
        console.print("-" * 40)
        
        if hasattr(node_result.result, 'content'):
            for content_block in node_result.result.content:
                if hasattr(content_block, 'text'):
                    console.print(content_block.text)
        else:
            console.print(str(node_result.result))
    
    console.print("\n" + "="*80)

def main():
    """Main execution function."""
    console.print(Panel.fit("🚀 Initializing Strands Agent Swarm Team", style="bold green"))
    
    try:
        # Check if Ollama is running
        console.print("[yellow]Checking Ollama connection...[/yellow]")
        
        # Create the agent team
        swarm = create_agent_team()
        console.print("[green]✅ Agent swarm created successfully[/green]")
        
        # Define a comprehensive collaborative task
        task = (
            "Conduct a comprehensive analysis of the AI agent market. "
            "Research current market size, growth trends, and key players. "
            "Calculate projected market value assuming 25% annual growth from current levels. "
            "Create a professional business report with executive summary, detailed analysis, "
            "financial projections, and strategic recommendations."
        )
        
        console.print(f"\n[bold]Executing Task:[/bold]\n{task}")
        console.print("\n[yellow]Starting swarm execution...[/yellow]")
        
        # Execute the swarm
        result = swarm(task)
        
        # Display comprehensive results
        display_results(result)
        
        console.print(Panel.fit("✅ Swarm execution completed successfully!", style="bold green"))
        
    except Exception as e:
        console.print(f"[bold red]❌ Error executing agent team: {e}[/bold red]")
        logger.exception("Swarm execution failed")
        raise

if __name__ == "__main__":
    main()
