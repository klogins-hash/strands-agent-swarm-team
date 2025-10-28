# Strands Agent Swarm Team 🤖

**Autonomous Multi-Agent System with Dynamic Team Creation**

A sophisticated AI system powered by Groq's Llama 3.3 70B that can autonomously analyze tasks, determine human-in-the-loop requirements, break down complex work into subtasks, and dynamically create the agents, tools, and orchestration needed to complete any task. Features a modern web dashboard for task management and full observability with PostgreSQL and Redis backend.

## 🌟 Features

- **🧠 Intelligent Swarm**: Multi-agent collaboration using Strands SDK
- **🔧 Specialized Agents**: Research, Analysis, and Writing specialists
- **🐳 Docker Ready**: Complete containerized deployment with PostgreSQL & Redis
- **📊 Rich Output**: Beautiful formatted results and progress tracking
- **🔄 Handoff System**: Seamless agent-to-agent task delegation
- **🚀 Groq API**: Powered by Llama 3.3 70B for high-performance inference

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Groq API key (get from https://console.groq.com/keys)

### 1. Clone and Setup
```bash
git clone https://github.com/klogins-hash/strands-agent-swarm-team.git
cd strands-agent-swarm-team
cp .env.example .env

# Edit .env and add your Groq API key
# GROQ_API_KEY=your_actual_groq_api_key_here
```

### 2. Deploy with Docker
```bash
# Start the entire stack
docker-compose up -d

# View logs
docker-compose logs -f agent-team
```

### 3. Manual Setup (Alternative)
```bash
# Install dependencies
pip install -r requirements.txt

# Start Ollama locally
ollama serve

# Pull the model
ollama pull llama3.2

# Run the agent team
python agent_team.py
```

## 🏗️ Architecture

```
┌─────────────────────┐
│   Task Input        │
└─────────┬───────────┘
          │
┌─────────▼───────────┐
│    RESEARCHER       │ ──┐
│  • web_search tool  │   │
│  • Market intel     │   │
└─────────────────────┘   │
          │               │
          │ handoff       │
          ▼               │
┌─────────────────────┐   │ SWARM
│     ANALYST         │   │ COORDINATION
│  • calculate tool   │   │
│  • Financial model  │   │
└─────────────────────┘   │
          │               │
          │ handoff       │
          ▼               │
┌─────────────────────┐   │
│      WRITER         │ ──┘
│  • format_report    │
│  • Professional    │
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│   Final Report      │
└─────────────────────┘
```

## 🤖 Agent Roles

### 🔍 Researcher Agent
- **Tools**: `web_search`
- **Specialty**: Market intelligence and data gathering
- **Handoff Logic**: Passes to Analyst for calculations, Writer for formatting

### 📊 Analyst Agent  
- **Tools**: `calculate`
- **Specialty**: Quantitative analysis and financial modeling
- **Handoff Logic**: Requests more data from Researcher, sends results to Writer

### ✍️ Writer Agent
- **Tools**: `format_report`
- **Specialty**: Professional report creation and synthesis
- **Handoff Logic**: Requests additional research or analysis as needed

## 📋 Example Tasks

The system excels at multi-step collaborative tasks:

```python
# Market Analysis Task
task = """
Conduct a comprehensive analysis of the AI agent market. 
Research current market size, growth trends, and key players. 
Calculate projected market value assuming 25% annual growth. 
Create a professional business report with recommendations.
"""

# The swarm will automatically:
# 1. Researcher gathers market data
# 2. Analyst performs growth calculations  
# 3. Writer creates formatted report
```

## 🐳 Docker Deployment

### Services
- **ollama**: Local LLM server (llama3.2 model)
- **agent-team**: Strands swarm application

### Configuration
```yaml
# docker-compose.yml includes:
- Ollama service with health checks
- Automatic model pulling
- Volume persistence
- Network connectivity
```

### Commands
```bash
# Start services
docker-compose up -d

# View agent execution
docker-compose logs -f agent-team

# Stop services  
docker-compose down

# Clean up (removes volumes)
docker-compose down -v
```

## 🔧 Configuration

### Environment Variables
```bash
# Model Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Alternative Providers
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Application Settings
LOG_LEVEL=INFO
MAX_AGENTS=10
AGENT_TIMEOUT=300
```

### Swarm Parameters
```python
swarm = Swarm(
    nodes=[researcher, analyst, writer],
    entry_point=researcher,
    max_handoffs=15,           # Max agent transitions
    max_iterations=20,         # Max total iterations
    execution_timeout=600.0,   # 10 minutes total
    node_timeout=120.0,        # 2 minutes per agent
    repetitive_handoff_detection_window=5,
    repetitive_handoff_min_unique_agents=2
)
```

## 📊 Output Example

```
🤖 STRANDS AGENT SWARM EXECUTION RESULTS
================================================================================
Status: COMPLETED
Execution Time: 45230ms
Total Agents Used: 3
Agent Sequence: researcher → analyst → writer
Token Usage: Input: 1250, Output: 2100, Total: 3350

📋 AGENT RESULTS
----------------------------------------------------------------

[RESEARCHER]
----------------------------------------
Search results for 'AI agent market':
• Size: The global AI market was valued at approximately $136.55 billion in 2022
• Growth: Expected to grow at a CAGR of 37.3% from 2023 to 2030
• Key Players: OpenAI, Google, Microsoft, Amazon, Anthropic, Meta

[ANALYST]  
----------------------------------------
Financial projection: $136.55B growing at 25.0% annually = $831.88B after 8 years
Market analysis shows strong fundamentals with consistent growth trajectory.

[WRITER]
----------------------------------------
# AI Agent Market Analysis Report

## Executive Summary
The AI agent market demonstrates exceptional growth potential with current 
valuation of $136.55B and projected expansion to $831.88B by 2030...

[Full professional report with recommendations]
```

## 🛠️ Development

### Local Development
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install dependencies
pip install -r requirements.txt

# Run with different models
python agent_team.py
```

### Adding New Agents
```python
# Create new specialized agent
specialist = Agent(
    name="specialist",
    model=model,
    system_prompt="Your specialized role...",
    tools=[custom_tool],
    description="Expert in specific domain"
)

# Add to swarm
swarm = Swarm(nodes=[researcher, analyst, writer, specialist])
```

### Custom Tools
```python
@tool
def custom_analysis(data: str) -> str:
    """Perform custom analysis on data."""
    # Your custom logic here
    return f"Analysis result: {processed_data}"
```

## 🔍 Monitoring & Debugging

### Logs
```bash
# Docker logs
docker-compose logs -f agent-team

# Local logs
tail -f logs/agent_team.log
```

### Health Checks
```bash
# Check Ollama
curl http://localhost:11434/api/version

# Check model availability
curl http://localhost:11434/api/tags
```

## 🚨 Troubleshooting

### Common Issues

1. **Ollama Connection Failed**
   ```bash
   # Check if Ollama is running
   docker-compose ps ollama
   
   # Restart Ollama service
   docker-compose restart ollama
   ```

2. **Model Not Found**
   ```bash
   # Pull model manually
   docker-compose exec ollama ollama pull llama3.2
   ```

3. **Out of Memory**
   ```bash
   # Use smaller model
   docker-compose exec ollama ollama pull llama3.2:1b
   ```

4. **Agent Timeout**
   - Increase `node_timeout` in swarm configuration
   - Check agent system prompts for clarity
   - Verify tool implementations

### Performance Optimization
- Use smaller models for faster responses
- Adjust timeout values based on task complexity
- Monitor token usage and optimize prompts
- Consider GPU acceleration for Ollama

## 📈 Scaling

### Horizontal Scaling
```yaml
# docker-compose.yml
agent-team:
  deploy:
    replicas: 3
  environment:
    - SWARM_ID=${HOSTNAME}
```

### Model Alternatives
```python
# Switch to cloud providers for better performance
from strands.models.openai import OpenAIModel
from strands.models.anthropic import AnthropicModel

model = OpenAIModel(model_id="gpt-4")
# or
model = AnthropicModel(model_id="claude-3-sonnet-20240229")
```

## 🔒 Security

- Ollama runs locally (no external API calls)
- No sensitive data leaves your environment
- Docker containers are isolated
- Environment variables for configuration

## 📄 License

This project is for educational and development purposes. Modify as needed for your requirements.

---

**Happy swarming! 🚀**

For questions or issues, check the logs and ensure all services are healthy.
