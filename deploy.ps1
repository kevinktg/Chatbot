# Gather Foods Data-Sovereign Chatbot Deployment Script (PowerShell)
# Complete local deployment with no external dependencies

param(
    [switch]$SkipChecks
)

Write-Host "🍃 Gather Foods Data-Sovereign Chatbot Deployment" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Green

# Check if Docker is installed
if (-not $SkipChecks) {
    try {
        docker --version | Out-Null
        Write-Host "✅ Docker is installed" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Docker is not installed. Please install Docker Desktop first." -ForegroundColor Red
        exit 1
    }

    # Check if Docker Compose is installed
    try {
        docker-compose --version | Out-Null
        Write-Host "✅ Docker Compose is installed" -ForegroundColor Green
    }
    catch {
        Write-Host "❌ Docker Compose is not installed. Please install Docker Compose first." -ForegroundColor Red
        exit 1
    }
}

# Check if model file exists
if (-not (Test-Path "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf")) {
    Write-Host "❌ Model file not found: DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf" -ForegroundColor Red
    Write-Host "Please ensure the model file is in the current directory." -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ Prerequisites check passed" -ForegroundColor Green

# Create necessary directories
Write-Host "📁 Creating directories..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path "data/raw", "data/interim", "data/processed", "data/index", "static", "models" | Out-Null

# Copy model to models directory
Write-Host "🤖 Setting up model..." -ForegroundColor Cyan
Copy-Item "DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf" "models/" -Force

# Build and start the container
Write-Host "🐳 Building and starting Docker container..." -ForegroundColor Cyan
docker-compose up --build -d

# Wait for the service to be ready
Write-Host "⏳ Waiting for service to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# Check health
Write-Host "🏥 Checking service health..." -ForegroundColor Cyan
$healthy = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -UseBasicParsing -TimeoutSec 5
        if ($response.StatusCode -eq 200) {
            Write-Host "✅ Service is healthy!" -ForegroundColor Green
            $healthy = $true
            break
        }
    }
    catch {
        Write-Host "⏳ Waiting for service to be ready... ($i/30)" -ForegroundColor Yellow
        Start-Sleep -Seconds 2
    }
}

if (-not $healthy) {
    Write-Host "⚠️  Service may not be fully ready. Check logs with: docker-compose logs" -ForegroundColor Yellow
}

# Show status
Write-Host ""
Write-Host "🎉 Deployment complete!" -ForegroundColor Green
Write-Host "======================" -ForegroundColor Green
Write-Host "🌐 Chatbot URL: http://localhost:8000" -ForegroundColor Cyan
Write-Host "🔍 Health Check: http://localhost:8000/api/health" -ForegroundColor Cyan
Write-Host "📊 API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 Features:" -ForegroundColor Yellow
Write-Host "   • Complete data sovereignty (no external API calls)" -ForegroundColor White
Write-Host "   • Local DeepSeek model inference" -ForegroundColor White
Write-Host "   • RAG-powered responses with company knowledge" -ForegroundColor White
Write-Host "   • Beautiful web interface" -ForegroundColor White
Write-Host "   • Session management" -ForegroundColor White
Write-Host ""
Write-Host "🛠️  Management commands:" -ForegroundColor Yellow
Write-Host "   • View logs: docker-compose logs -f" -ForegroundColor White
Write-Host "   • Stop service: docker-compose down" -ForegroundColor White
Write-Host "   • Restart service: docker-compose restart" -ForegroundColor White
Write-Host "   • Update: docker-compose up --build -d" -ForegroundColor White
Write-Host ""
Write-Host "🔒 Data Sovereignty:" -ForegroundColor Yellow
Write-Host "   • All data stays local" -ForegroundColor White
Write-Host "   • No external API dependencies" -ForegroundColor White
Write-Host "   • Model runs entirely on your infrastructure" -ForegroundColor White
Write-Host "   • Company knowledge is private and secure" -ForegroundColor White
Write-Host ""
Write-Host "🚀 Opening browser..." -ForegroundColor Cyan
Start-Process "http://localhost:8000"
