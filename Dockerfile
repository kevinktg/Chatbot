# Gather Foods Data-Sovereign Chatbot Dockerfile
# Complete local deployment with no external dependencies

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml requirements.txt* ./

# Copy the entire application
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir llama-cpp-python


# Create directories for data
RUN mkdir -p data/raw data/interim data/processed data/index static

# Copy the model file (if it exists)
COPY DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf ./

# Set environment variables
ENV PYTHONPATH=/app
ENV TRAINING_DEVICE=cpu
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the chatbot
CMD ["python", "chatbot.py"]
