# Project: AI Voice Assistant

## Project Overview

This project is a full-stack AI-powered voice assistant. It combines a Python backend for training and retrieval with a Next.js frontend for a modern, voice-powered user interface. The backend uses a low-resource training and retrieval pipeline for small datasets, including PDF and JSON ingestion, semantic chunking, embeddings, and a FAISS index. The frontend is built with Next.js, Three.js, and ElevenLabs for premium voice synthesis. The entire solution is designed to be containerized with Docker for easy deployment and data sovereignty.

**Backend Key Technologies:**

*   Python
*   FastAPI
*   PyTorch
*   Sentence-transformers
*   FAISS
*   Docker

**Frontend Key Technologies:**

*   Next.js
*   React
*   TypeScript
*   Three.js
*   Framer Motion
*   Tailwind CSS
*   ElevenLabs API

## Building and Running

### Backend (Python)

1.  **Create and activate a virtual environment:**

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install dependencies:**

    ```bash
    pip install -e .
    ```

3.  **Build the index:**

    ```bash
    python -m training.cli ingest --pdf data/raw/source.pdf --json data/raw/gf2025-main.json
    python -m training.cli chunk --chunker chonkie
    python -m training.cli embed --model bge-small-en
    python -m training.cli index --metric cosine --faiss-type flat
    ```

4.  **Run the server:**

    ```bash
    uvicorn training.api:app --host 0.0.0.0 --port 8000
    ```

### Frontend (Next.js)

1.  **Install dependencies:**

    ```bash
    npm install
    ```

2.  **Set up environment variables:**

    Create a `.env.local` file and add your ElevenLabs API key:

    ```
    ELEVENLABS_API_KEY=your_actual_api_key_here
    BACKEND_URL=http://localhost:8000
    NEXT_PUBLIC_APP_URL=http://localhost:3000
    ```

3.  **Run the development server:**

    ```bash
    npm run dev
    ```

### Docker

1.  **Prerequisites:**
    *   Docker Desktop installed
    *   The `DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf` model file in the project directory

2.  **Deploy in one command (Windows):**

    ```powershell
    .\deploy.ps1
    ```

3.  **Manual Deployment:**

    ```bash
    docker-compose up --build -d
    ```

## Development Conventions

*   **Python:**
    *   The project follows the structure outlined in the main `README.md` file.
    *   Code is organized into modules for ingestion, chunking, embedding, indexing, and API.
    *   The project uses `ruff` for linting and `mypy` for type checking.
*   **Next.js:**
    *   The frontend follows the structure outlined in the `README-NEXTJS.md` file.
    *   Components are used to create a modular and maintainable user interface.
    *   The project uses ESLint for linting and TypeScript for type checking.
*   **Deployment:**
    *   The project is designed to be deployed using Docker for data sovereignty and ease of use.
    *   The `README-DEPLOYMENT.md` file provides detailed instructions for deployment and management.
