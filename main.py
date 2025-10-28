#!/usr/bin/env python3
"""
Main entry point for the Strands Agent Swarm Team
Autonomous multi-agent system with web dashboard.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
console = Console()

def check_groq_api_key():
    """Check if Groq API key is configured."""
    return bool(os.getenv("GROQ_API_KEY") and os.getenv("GROQ_API_KEY") != "your_groq_api_key_here")

def display_startup_info():
    """Display startup information."""
    console.print(Panel.fit(
        Text("🤖 Strands Agent Swarm Team", style="bold blue"),
        subtitle="Autonomous Multi-Agent System"
    ))
    
    console.print("\n[bold green]✅ System Features:[/bold green]")
    console.print("• 🧠 Autonomous task analysis and breakdown")
    console.print("• 🔧 Dynamic agent and tool creation")
    console.print("• 📊 Web dashboard with conversation management")
    console.print("• 🔄 Human-in-the-loop approval system")
    console.print("• 📈 Real-time observability and metrics")
    
    console.print(f"\n[bold blue]🌐 Dashboard URL:[/bold blue] http://localhost:8000")
    console.print(f"[bold blue]📡 WebSocket:[/bold blue] ws://localhost:8000/ws")
    
    # Check Groq API key status
    if check_groq_api_key():
        console.print("[bold green]✅ Groq API:[/bold green] Llama 3.3 70B configured")
    else:
        console.print("[bold red]❌ Groq API:[/bold red] API key not configured")
        console.print("   Set GROQ_API_KEY environment variable")
        console.print("   Get your API key from: [link]https://console.groq.com/keys[/link]")

def main():
    """Main entry point."""
    try:
        display_startup_info()
        
        # Create necessary directories
        os.makedirs("logs", exist_ok=True)
        os.makedirs("data", exist_ok=True)
        
        console.print("\n[bold green]🚀 Starting Strands Agent Swarm Team...[/bold green]")
        
        # Start the web application
        uvicorn.run(
            "web.app:app",
            host="0.0.0.0",
            port=8000,
            reload=False,  # Disable reload for production
            log_level="info"
        )
        
    except KeyboardInterrupt:
        console.print("\n[bold yellow]👋 Shutting down gracefully...[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Error starting system: {e}[/bold red]")
        logger.exception("Startup error")
        sys.exit(1)

if __name__ == "__main__":
    main()
