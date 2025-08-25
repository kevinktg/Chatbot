#!/bin/bash

# Gather Foods Data-Sovereign Chatbot Deployment Script
# Complete local deployment with no external dependencies

set -e

echo "🍃 Gather Foods Data-Sovereign Chatbot Deployment"
echo "=================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if model file exists
if [ ! -f "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf" ]; then
    echo "❌ Model file not found: DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf"
    echo "Please ensure the model file is in the current directory."
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/raw data/interim data/processed data/index static models

# Copy model to models directory
echo "🤖 Setting up model..."
cp DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf models/

# Build and start the container
echo "🐳 Building and starting Docker container..."
docker-compose up --build -d

# Wait for the service to be ready
echo "⏳ Waiting for service to be ready..."
sleep 10

# Check health
echo "🏥 Checking service health..."
for i in {1..30}; do
    if curl -f http://localhost:8000/api/health &> /dev/null; then
        echo "✅ Service is healthy!"
        break
    fi
    echo "⏳ Waiting for service to be ready... ($i/30)"
    sleep 2
done

# Show status
echo ""
echo "🎉 Deployment complete!"
echo "======================"
echo "🌐 Chatbot URL: http://localhost:8000"
echo "🔍 Health Check: http://localhost:8000/api/health"
echo "📊 API Docs: http://localhost:8000/docs"
echo ""
echo "💡 Features:"
echo "   • Complete data sovereignty (no external API calls)"
echo "   • Local DeepSeek model inference"
echo "   • RAG-powered responses with company knowledge"
echo "   • Beautiful web interface"
echo "   • Session management"
echo ""
echo "🛠️  Management commands:"
echo "   • View logs: docker-compose logs -f"
echo "   • Stop service: docker-compose down"
echo "   • Restart service: docker-compose restart"
echo "   • Update: docker-compose up --build -d"
echo ""
echo "🔒 Data Sovereignty:"
echo "   • All data stays local"
echo "   • No external API dependencies"
echo "   • Model runs entirely on your infrastructure"
echo "   • Company knowledge is private and secure"
