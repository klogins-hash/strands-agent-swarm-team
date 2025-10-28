#!/bin/bash

# Strands Agent Swarm Team - Deployment Script

set -e

echo "🤖 Strands Agent Swarm Team Deployment"
echo "======================================"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose not found. Please install Docker Compose."
    exit 1
fi

echo "✅ Docker is running"

# Create necessary directories
mkdir -p logs data web/static

echo "📁 Created directories"

# Build and start services
echo "🏗️  Building and starting services..."
docker-compose up --build -d

echo "⏳ Waiting for services to be ready..."

# Wait for services to be healthy
echo "🔄 Waiting for services to start..."

# Wait for PostgreSQL
echo "   Waiting for PostgreSQL..."
timeout=120
counter=0
while [ $counter -lt $timeout ]; do
    if docker-compose exec -T postgres pg_isready -U strands_user -d strands_db > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready"
        break
    fi
    sleep 3
    counter=$((counter + 3))
    echo "      Still waiting... (${counter}s/${timeout}s)"
done

if [ $counter -ge $timeout ]; then
    echo "❌ PostgreSQL failed to start within ${timeout} seconds"
    docker-compose logs postgres
    exit 1
fi

# Wait for Redis
echo "   Waiting for Redis..."
timeout=60
counter=0
while [ $counter -lt $timeout ]; do
    if docker-compose exec -T redis redis-cli -a strands_redis_pass ping > /dev/null 2>&1; then
        echo "✅ Redis is ready"
        break
    fi
    sleep 2
    counter=$((counter + 2))
    echo "      Still waiting... (${counter}s/${timeout}s)"
done

if [ $counter -ge $timeout ]; then
    echo "❌ Redis failed to start within ${timeout} seconds"
    docker-compose logs redis
    exit 1
fi

# Wait for agent team to be ready
echo "🔄 Waiting for Agent Team to start..."
timeout=120
counter=0
while [ $counter -lt $timeout ]; do
    if curl -f http://localhost:8000/api/metrics > /dev/null 2>&1; then
        echo "✅ Agent Team is ready"
        break
    fi
    sleep 5
    counter=$((counter + 5))
    echo "   Still waiting... (${counter}s/${timeout}s)"
done

if [ $counter -ge $timeout ]; then
    echo "❌ Agent Team failed to start within ${timeout} seconds"
    docker-compose logs agent-team
    exit 1
fi

echo ""
echo "🎉 Strands Agent Swarm Team is now running!"
echo ""
echo "📊 Dashboard: http://localhost:8000"
echo "📋 Projects: http://localhost:8000/projects"
echo "🚀 Groq API: Llama 3.3 70B (via API)"
echo "🐘 PostgreSQL: localhost:5432 (strands_db)"
echo "🗄️  Redis: localhost:6379"
echo ""
echo "📋 Management Commands:"
echo "  View logs:     docker-compose logs -f"
echo "  Stop system:   docker-compose down"
echo "  Restart:       docker-compose restart"
echo "  Clean reset:   docker-compose down -v && ./run.sh"
echo "  DB shell:      docker-compose exec postgres psql -U strands_user -d strands_db"
echo "  Redis CLI:     docker-compose exec redis redis-cli -a strands_redis_pass"
echo ""
echo "🔍 System Status:"
docker-compose ps

echo ""
echo "✨ Ready to receive tasks! Open http://localhost:8000 in your browser."
