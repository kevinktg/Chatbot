#!/usr/bin/env python3
"""
Gather Foods AI Startup - Voice-Enabled Chatbot
Advanced TTS/STT with Three.js 3D visualizations
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import numpy as np
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import uvicorn

# Import our existing RAG components
from training.config import settings
from training.embed.embedder import EmbeddingRunner
from training.index.faiss_store import FaissStore

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
_rag_store: Optional[FaissStore] = None
_rag_runner: Optional[EmbeddingRunner] = None
_chunk_lookup: Optional[Dict[str, Dict]] = None
_llm_model = None

@dataclass
class ChatMessage:
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime
    metadata: Optional[Dict] = None

class ChatSession:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: List[ChatMessage] = []
        self.context_window = 10
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        message = ChatMessage(
            role=role,
            content=content,
            timestamp=datetime.now(),
            metadata=metadata
        )
        self.messages.append(message)
        
        if len(self.messages) > self.context_window:
            self.messages = self.messages[-self.context_window:]
    
    def get_context(self) -> str:
        context_parts = []
        for msg in self.messages[-6:]:
            context_parts.append(f"{msg.role.title()}: {msg.content}")
        return "\n".join(context_parts)

class GatherFoodsChatbot:
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
        self._initialize_rag()
        self._initialize_llm()
    
    def _initialize_rag(self):
        global _rag_store, _rag_runner, _chunk_lookup
        
        try:
            if not (settings.index_dir / "index.faiss").exists():
                logger.warning("FAISS index not found. RAG features will be disabled.")
                return
            
            _rag_store = FaissStore.load(settings.index_dir)
            _rag_runner = EmbeddingRunner(model_name=settings.embed_model, device=settings.device)
            
            chunk_path = settings.data_processed / "chunks.jsonl"
            if chunk_path.exists():
                _chunk_lookup = {}
                with chunk_path.open("r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            obj = json.loads(line)
                            _chunk_lookup[obj["id"]] = obj
                
                logger.info(f"RAG system initialized with {len(_chunk_lookup)} chunks")
            else:
                logger.warning("Chunk lookup not found")
                
        except Exception as e:
            logger.error(f"Failed to initialize RAG: {e}")
    
    def _initialize_llm(self):
        global _llm_model
        
        try:
            from llama_cpp import Llama
            
            model_path = Path("DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf")
            if not model_path.exists():
                logger.error(f"Model file not found: {model_path}")
                return
            
            _llm_model = Llama(
                model_path=str(model_path),
                n_ctx=4096,
                n_threads=4,
                n_gpu_layers=0,
                verbose=False
            )
            
            logger.info("Local LLM initialized successfully")
            
        except ImportError:
            logger.error("llama-cpp-python not installed. Install with: pip install llama-cpp-python")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
    
    def _retrieve_context(self, query: str, top_k: int = 3) -> str:
        if not _rag_store or not _rag_runner or not _chunk_lookup:
            return ""
        
        try:
            query_vec = _rag_runner.encode_text(query)
            hits = _rag_store.search(query_vec, top_k=top_k)
            
            context_parts = []
            for hit in hits:
                chunk_id = hit["id"]
                chunk_data = _chunk_lookup.get(chunk_id, {})
                text = chunk_data.get("text", "")
                if text:
                    context_parts.append(f"Context: {text}")
            
            return "\n\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}")
            return ""
    
    def _generate_response(self, prompt: str) -> str:
        if not _llm_model:
            return "I'm sorry, but I'm currently unable to generate responses. Please check the system configuration."
        
        try:
            system_prompt = """You are an advanced AI assistant for Gather Foods, an Aboriginal-owned catering company. 
            You help customers with menu inquiries, dietary requirements, pricing, and company information.
            Always be respectful of Aboriginal culture and heritage. Provide accurate, helpful information based on the context provided."""
            
            full_prompt = f"{system_prompt}\n\n{prompt}"
            
            response = _llm_model(
                full_prompt,
                max_tokens=512,
                temperature=0.7,
                stop=["User:", "Human:", "\n\n"]
            )
            
            return response["choices"][0]["text"].strip()
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return "I apologize, but I encountered an error generating a response. Please try again."
    
    def chat(self, session_id: str, user_message: str) -> str:
        if session_id not in self.sessions:
            self.sessions[session_id] = ChatSession(session_id)
        
        session = self.sessions[session_id]
        session.add_message("user", user_message)
        
        context = self._retrieve_context(user_message)
        conversation_context = session.get_context()
        
        if context:
            prompt = f"""Based on the following information about Gather Foods:

{context}

And our conversation so far:
{conversation_context}

Please provide a helpful response to: {user_message}

Remember: You are representing Gather Foods, an Aboriginal-owned catering company that combines 60,000 years of indigenous knowledge with modern innovation. Be respectful, accurate, and helpful."""
        else:
            prompt = f"""You are a helpful AI assistant for Gather Foods, an Aboriginal-owned catering company.

Our conversation so far:
{conversation_context}

Please provide a helpful response to: {user_message}

Remember: You are representing Gather Foods, an Aboriginal-owned catering company that combines 60,000 years of indigenous knowledge with modern innovation. Be respectful, accurate, and helpful."""
        
        response = self._generate_response(prompt)
        session.add_message("assistant", response, metadata={"context_used": bool(context)})
        
        return response

# Initialize chatbot
chatbot = GatherFoodsChatbot()

# FastAPI app
app = FastAPI(title="Gather Foods AI Voice Assistant")

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# API Models
class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str
    session_id: str
    timestamp: str
    context_used: bool = False

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        response = chatbot.chat(request.session_id, request.message)
        
        session = chatbot.sessions.get(request.session_id)
        context_used = False
        if session and session.messages:
            last_msg = session.messages[-1]
            context_used = last_msg.metadata.get("context_used", False) if last_msg.metadata else False
        
        return ChatResponse(
            response=response,
            session_id=request.session_id,
            timestamp=datetime.now().isoformat(),
            context_used=context_used
        )
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "rag_available": _rag_store is not None,
        "llm_available": _llm_model is not None,
        "active_sessions": len(chatbot.sessions)
    }

@app.get("/", response_class=HTMLResponse)
async def voice_interface():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Gather Foods AI Voice Assistant</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }

            body {
                font-family: 'Inter', sans-serif;
                background: #000;
                min-height: 100vh;
                overflow: hidden;
                position: relative;
            }

            #threejs-container {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                z-index: 1;
            }

            .main-container {
                position: relative;
                z-index: 10;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                padding: 20px;
            }

            .header {
                text-align: center;
                margin-bottom: 40px;
                color: white;
            }

            .header h1 {
                font-size: 3.5rem;
                font-weight: 700;
                margin-bottom: 10px;
                background: linear-gradient(45deg, #fff, #f0f0f0);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                text-shadow: 0 0 30px rgba(255, 255, 255, 0.3);
            }

            .header p {
                font-size: 1.2rem;
                opacity: 0.9;
                font-weight: 300;
            }

            .voice-interface {
                background: rgba(255, 255, 255, 0.1);
                backdrop-filter: blur(20px);
                border-radius: 30px;
                padding: 40px;
                box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.2);
                max-width: 600px;
                width: 100%;
                text-align: center;
            }

            .voice-visualization {
                position: relative;
                width: 200px;
                height: 200px;
                margin: 0 auto 30px;
                display: flex;
                align-items: center;
                justify-content: center;
            }

            .voice-circle {
                width: 150px;
                height: 150px;
                border-radius: 50%;
                background: linear-gradient(45deg, #4CAF50, #45a049);
                display: flex;
                align-items: center;
                justify-content: center;
                position: relative;
                transition: all 0.3s ease;
                cursor: pointer;
                box-shadow: 0 0 30px rgba(76, 175, 80, 0.5);
            }

            .voice-circle:hover {
                transform: scale(1.05);
                box-shadow: 0 0 50px rgba(76, 175, 80, 0.8);
            }

            .voice-circle.listening {
                animation: pulse 1.5s ease-in-out infinite;
                background: linear-gradient(45deg, #ff6b6b, #ee5a52);
                box-shadow: 0 0 50px rgba(255, 107, 107, 0.8);
            }

            @keyframes pulse {
                0% { transform: scale(1); }
                50% { transform: scale(1.1); }
                100% { transform: scale(1); }
            }

            .voice-icon {
                font-size: 2.5rem;
                color: white;
            }

            .voice-status {
                font-size: 1.1rem;
                color: white;
                margin-bottom: 20px;
                font-weight: 500;
            }

            .controls {
                display: flex;
                gap: 15px;
                justify-content: center;
                margin-bottom: 30px;
            }

            .control-btn {
                background: rgba(255, 255, 255, 0.2);
                border: none;
                padding: 12px 24px;
                border-radius: 25px;
                color: white;
                font-size: 0.9rem;
                cursor: pointer;
                transition: all 0.3s ease;
                backdrop-filter: blur(10px);
            }

            .control-btn:hover {
                background: rgba(255, 255, 255, 0.3);
                transform: translateY(-2px);
            }

            .control-btn.active {
                background: rgba(76, 175, 80, 0.8);
            }

            .chat-container {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 20px;
                max-height: 300px;
                overflow-y: auto;
                margin-bottom: 20px;
                backdrop-filter: blur(10px);
            }

            .message {
                margin-bottom: 15px;
                display: flex;
                align-items: flex-start;
            }

            .message.user {
                justify-content: flex-end;
            }

            .message-content {
                max-width: 80%;
                padding: 12px 16px;
                border-radius: 18px;
                word-wrap: break-word;
                font-size: 0.9rem;
            }

            .message.user .message-content {
                background: rgba(76, 175, 80, 0.8);
                color: white;
            }

            .message.assistant .message-content {
                background: rgba(255, 255, 255, 0.9);
                color: #333;
            }

            .input-container {
                display: flex;
                gap: 10px;
                align-items: center;
            }

            .text-input {
                flex: 1;
                background: rgba(255, 255, 255, 0.2);
                border: none;
                padding: 15px 20px;
                border-radius: 25px;
                color: white;
                font-size: 1rem;
                backdrop-filter: blur(10px);
            }

            .text-input::placeholder {
                color: rgba(255, 255, 255, 0.7);
            }

            .text-input:focus {
                outline: none;
                background: rgba(255, 255, 255, 0.3);
            }

            .send-btn {
                background: rgba(76, 175, 80, 0.8);
                border: none;
                padding: 15px 20px;
                border-radius: 25px;
                color: white;
                cursor: pointer;
                transition: all 0.3s ease;
            }

            .send-btn:hover {
                background: rgba(76, 175, 80, 1);
                transform: translateY(-2px);
            }

            .status-bar {
                position: fixed;
                bottom: 20px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(0, 0, 0, 0.7);
                color: white;
                padding: 10px 20px;
                border-radius: 25px;
                font-size: 0.8rem;
                backdrop-filter: blur(10px);
            }

            .typing-indicator {
                display: none;
                color: rgba(255, 255, 255, 0.8);
                font-style: italic;
                margin-top: 10px;
            }

            @media (max-width: 768px) {
                .header h1 {
                    font-size: 2.5rem;
                }
                
                .voice-interface {
                    padding: 20px;
                }
                
                .voice-circle {
                    width: 120px;
                    height: 120px;
                }
                
                .voice-icon {
                    font-size: 2rem;
                }
            }
        </style>
    </head>
    <body>
        <div id="threejs-container"></div>
        
        <div class="main-container">
            <div class="header">
                <h1>🍃 Gather Foods AI</h1>
                <p>Voice-Powered Indigenous Knowledge Assistant</p>
            </div>
            
            <div class="voice-interface">
                <div class="voice-visualization">
                    <div class="voice-circle" id="voiceCircle">
                        <div class="voice-icon" id="voiceIcon">🎤</div>
                    </div>
                </div>
                
                <div class="voice-status" id="voiceStatus">
                    Click to start voice conversation
                </div>
                
                <div class="controls">
                    <button class="control-btn" id="voiceBtn">Voice</button>
                    <button class="control-btn" id="textBtn">Text</button>
                    <button class="control-btn" id="clearBtn">Clear</button>
                </div>
                
                <div class="chat-container" id="chatContainer">
                    <div class="message assistant">
                        <div class="message-content">
                            Welcome to Gather Foods AI! I'm your voice-powered assistant. Ask me about our menu, dietary options, or company heritage. Click the microphone to start speaking!
                        </div>
                    </div>
                </div>
                
                <div class="input-container">
                    <input type="text" class="text-input" id="textInput" 
                           placeholder="Type your question here..." 
                           autocomplete="off">
                    <button class="send-btn" id="sendBtn">Send</button>
                </div>
                
                <div class="typing-indicator" id="typingIndicator">
                    AI is thinking...
                </div>
            </div>
        </div>
        
        <div class="status-bar" id="statusBar">
            🔒 Data-Sovereign AI • Powered by Local DeepSeek Model
        </div>

        <script>
            // Three.js Scene Setup
            let scene, camera, renderer, particles, voiceWaves;
            let isListening = false;

            function initThreeJS() {
                // Scene
                scene = new THREE.Scene();
                
                // Camera
                camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
                camera.position.z = 5;
                
                // Renderer
                renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
                renderer.setSize(window.innerWidth, window.innerHeight);
                renderer.setClearColor(0x000000, 0);
                document.getElementById('threejs-container').appendChild(renderer.domElement);
                
                // Create floating particles
                createParticles();
                
                // Create voice waves
                createVoiceWaves();
                
                // Animation loop
                animate();
                
                // Handle window resize
                window.addEventListener('resize', onWindowResize);
            }

            function createParticles() {
                const particleCount = 100;
                const geometry = new THREE.BufferGeometry();
                const positions = new Float32Array(particleCount * 3);
                const colors = new Float32Array(particleCount * 3);
                
                for (let i = 0; i < particleCount * 3; i += 3) {
                    positions[i] = (Math.random() - 0.5) * 20;
                    positions[i + 1] = (Math.random() - 0.5) * 20;
                    positions[i + 2] = (Math.random() - 0.5) * 20;
                    
                    colors[i] = Math.random() * 0.5 + 0.5;
                    colors[i + 1] = Math.random() * 0.5 + 0.5;
                    colors[i + 2] = Math.random() * 0.5 + 0.5;
                }
                
                geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
                geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
                
                const material = new THREE.PointsMaterial({
                    size: 0.05,
                    vertexColors: true,
                    transparent: true,
                    opacity: 0.8
                });
                
                particles = new THREE.Points(geometry, material);
                scene.add(particles);
            }

            function createVoiceWaves() {
                voiceWaves = [];
                const waveCount = 4;
                
                for (let i = 0; i < waveCount; i++) {
                    const geometry = new THREE.RingGeometry(0.5 + i * 0.3, 0.6 + i * 0.3, 32);
                    const material = new THREE.MeshBasicMaterial({
                        color: 0x4CAF50,
                        transparent: true,
                        opacity: 0.3,
                        side: THREE.DoubleSide
                    });
                    
                    const wave = new THREE.Mesh(geometry, material);
                    wave.visible = false;
                    voiceWaves.push(wave);
                    scene.add(wave);
                }
            }

            function animate() {
                requestAnimationFrame(animate);
                
                // Rotate particles
                if (particles) {
                    particles.rotation.x += 0.001;
                    particles.rotation.y += 0.002;
                }
                
                // Animate voice waves
                if (isListening) {
                    voiceWaves.forEach((wave, index) => {
                        wave.visible = true;
                        wave.scale.setScalar(1 + Math.sin(Date.now() * 0.003 + index) * 0.2);
                        wave.material.opacity = 0.3 + Math.sin(Date.now() * 0.002 + index) * 0.2;
                        wave.material.color.setHex(isListening ? 0xff6b6b : 0x4CAF50);
                    });
                } else {
                    voiceWaves.forEach(wave => {
                        wave.visible = false;
                    });
                }
                
                renderer.render(scene, camera);
            }

            function onWindowResize() {
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, window.innerHeight);
            }

            // Voice recognition setup
            let recognition;
            let sessionId = 'session_' + Date.now();

            if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
                recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
                recognition.continuous = false;
                recognition.interimResults = false;
                recognition.lang = 'en-US';
            }

            // DOM elements
            const voiceCircle = document.getElementById('voiceCircle');
            const voiceIcon = document.getElementById('voiceIcon');
            const voiceStatus = document.getElementById('voiceStatus');
            const chatContainer = document.getElementById('chatContainer');
            const textInput = document.getElementById('textInput');
            const sendBtn = document.getElementById('sendBtn');
            const voiceBtn = document.getElementById('voiceBtn');
            const textBtn = document.getElementById('textBtn');
            const clearBtn = document.getElementById('clearBtn');
            const typingIndicator = document.getElementById('typingIndicator');
            const statusBar = document.getElementById('statusBar');

            // Voice recognition events
            if (recognition) {
                recognition.onstart = () => {
                    isListening = true;
                    voiceCircle.classList.add('listening');
                    voiceIcon.textContent = '🔴';
                    voiceStatus.textContent = 'Listening... Speak now!';
                };

                recognition.onresult = (event) => {
                    const transcript = event.results[0][0].transcript;
                    addMessage(transcript, true);
                    processMessage(transcript);
                };

                recognition.onend = () => {
                    isListening = false;
                    voiceCircle.classList.remove('listening');
                    voiceIcon.textContent = '🎤';
                    voiceStatus.textContent = 'Click to start voice conversation';
                };

                recognition.onerror = (event) => {
                    console.error('Speech recognition error:', event.error);
                    voiceStatus.textContent = 'Voice recognition error. Try again.';
                    isListening = false;
                    voiceCircle.classList.remove('listening');
                    voiceIcon.textContent = '🎤';
                };
            }

            // Voice circle click
            voiceCircle.addEventListener('click', () => {
                if (recognition && !isListening) {
                    recognition.start();
                } else if (recognition && isListening) {
                    recognition.stop();
                }
            });

            // Control buttons
            voiceBtn.addEventListener('click', () => {
                voiceBtn.classList.add('active');
                textBtn.classList.remove('active');
                voiceCircle.style.display = 'flex';
                textInput.style.display = 'none';
                sendBtn.style.display = 'none';
            });

            textBtn.addEventListener('click', () => {
                textBtn.classList.add('active');
                voiceBtn.classList.remove('active');
                voiceCircle.style.display = 'none';
                textInput.style.display = 'block';
                sendBtn.style.display = 'block';
            });

            clearBtn.addEventListener('click', () => {
                chatContainer.innerHTML = `
                    <div class="message assistant">
                        <div class="message-content">
                            Welcome to Gather Foods AI! I'm your voice-powered assistant. Ask me about our menu, dietary options, or company heritage. Click the microphone to start speaking!
                        </div>
                    </div>
                `;
            });

            // Text input handling
            sendBtn.addEventListener('click', () => {
                const message = textInput.value.trim();
                if (message) {
                    addMessage(message, true);
                    processMessage(message);
                    textInput.value = '';
                }
            });

            textInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const message = textInput.value.trim();
                    if (message) {
                        addMessage(message, true);
                        processMessage(message);
                        textInput.value = '';
                    }
                }
            });

            // Message handling
            function addMessage(content, isUser = false) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
                
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                contentDiv.textContent = content;
                
                messageDiv.appendChild(contentDiv);
                chatContainer.appendChild(messageDiv);
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }

            async function processMessage(message) {
                showTyping();
                
                try {
                    const response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            message: message,
                            session_id: sessionId
                        })
                    });

                    const data = await response.json();
                    
                    if (response.ok) {
                        hideTyping();
                        addMessage(data.response);
                        
                        // Update status if context was used
                        if (data.context_used) {
                            statusBar.textContent = '🔒 Data-Sovereign AI • Using Indigenous Knowledge • Powered by Local DeepSeek Model';
                        }
                        
                        // Speak the response if voice mode is active
                        if (voiceBtn.classList.contains('active') && 'speechSynthesis' in window) {
                            const utterance = new SpeechSynthesisUtterance(data.response);
                            utterance.rate = 0.9;
                            utterance.pitch = 1;
                            speechSynthesis.speak(utterance);
                        }
                    } else {
                        hideTyping();
                        addMessage('Sorry, I encountered an error. Please try again.');
                    }
                } catch (error) {
                    hideTyping();
                    addMessage('Sorry, I\'m having trouble connecting. Please check your connection.');
                    console.error('Error:', error);
                }
            }

            function showTyping() {
                typingIndicator.style.display = 'block';
                chatContainer.scrollTop = chatContainer.scrollHeight;
            }

            function hideTyping() {
                typingIndicator.style.display = 'none';
            }

            // Initialize
            initThreeJS();
            voiceBtn.classList.add('active'); // Start in voice mode
        </script>
    </body>
    </html>
    """

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
