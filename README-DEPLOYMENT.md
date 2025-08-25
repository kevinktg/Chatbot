# 🍃 Gather Foods Data-Sovereign Chatbot

A complete, containerized chatbot solution for Gather Foods that ensures **100% data sovereignty** with no external API dependencies.

## 🎯 What You Get

- **🤖 Complete Chatbot**: Conversational interface with memory and context
- **🔒 Data Sovereignty**: Everything runs locally - no external API calls
- **🧠 Local AI**: DeepSeek-R1-Distill-Qwen-1.5B model runs on your infrastructure
- **📚 RAG Integration**: Company knowledge from menu and facts
- **🌐 Web Interface**: Beautiful, responsive chat interface
- **🐳 Docker Ready**: One-command deployment
- **📊 Monitoring**: Health checks and logging

## 🚀 Quick Start (Windows)

### Prerequisites
- Docker Desktop installed
- The `DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf` model file in the project directory

### Deploy in One Command
```powershell
.\deploy.ps1
```

This will:
1. ✅ Check prerequisites
2. 📁 Create necessary directories
3. 🤖 Set up the model
4. 🐳 Build and start the Docker container
5. 🏥 Verify the service is healthy
6. 🌐 Open your browser to the chatbot

### Manual Deployment
```powershell
# Build and start
docker-compose up --build -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

## 🌐 Access Points

- **Chat Interface**: http://localhost:8000
- **Health Check**: http://localhost:8000/api/health
- **API Documentation**: http://localhost:8000/docs

## 🔧 Management Commands

```powershell
# View logs
docker-compose logs -f

# Stop service
docker-compose down

# Restart service
docker-compose restart

# Update and rebuild
docker-compose up --build -d

# Check resource usage
docker stats gather-foods-chatbot
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Container                         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Web UI    │  │   FastAPI   │  │   Local     │        │
│  │  (Port 8000)│  │    Server   │  │   DeepSeek  │        │
│  └─────────────┘  └─────────────┘  │    Model    │        │
│                    ┌─────────────┐  └─────────────┘        │
│                    │   RAG       │                         │
│                    │   System    │  ┌─────────────┐        │
│                    │  (FAISS +   │  │   Session   │        │
│                    │   Embeddings)│  │ Management  │        │
│                    └─────────────┘  └─────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Data Sovereignty Features

### ✅ What Stays Local
- **AI Model**: DeepSeek-R1-Distill-Qwen-1.5B runs entirely on your hardware
- **Company Data**: Menu items, pricing, dietary info, company facts
- **Conversations**: All chat sessions stored locally
- **Embeddings**: Vector representations of your knowledge
- **Processing**: All AI inference happens on your infrastructure

### ❌ What Never Leaves Your Network
- No API calls to OpenAI, Google, or other external services
- No data sent to third-party servers
- No model weights uploaded anywhere
- No conversation logs shared externally

## 🎨 Features

### Chat Interface
- **Real-time Chat**: Instant responses with typing indicators
- **Session Memory**: Remembers conversation context
- **Rich Responses**: Context-aware answers using company knowledge
- **Mobile Responsive**: Works on all devices

### RAG Integration
- **Menu Knowledge**: 734+ menu items with pricing and dietary info
- **Company Facts**: 765+ facts about Aboriginal heritage and business
- **Semantic Search**: Finds relevant information for any query
- **Context Injection**: Provides relevant context to the AI model

### AI Capabilities
- **Natural Conversations**: Human-like responses
- **Cultural Awareness**: Respectful of Aboriginal heritage
- **Dietary Expertise**: Knowledge of vegetarian, gluten-free options
- **Pricing Information**: Accurate menu pricing and serving sizes

## 🔍 Example Conversations

**User**: "What vegetarian options do you have?"
**Bot**: "Gather Foods offers several delicious vegetarian options! We have Wattleseed Damper with native thyme cream cheese ($4.00), Croissant with cheese, bush tomato, and native thyme ($5.00), and Goats cheese tartlettes with bush tomato and native thyme ($5.40). All our vegetarian options incorporate native Australian ingredients and are inspired by traditional bush tucker."

**User**: "Tell me about your company"
**Bot**: "Gather Foods is a majority Aboriginal-owned business that combines 60,000 years of indigenous knowledge with modern entrepreneurial innovation. We were crowned 'Best Condiments & Ice Cream Company Australia 2023' and our products are inspired by native Australian ingredients and bush tucker. We create unique products that honor our heritage while meeting modern catering needs."

## 🛠️ Customization

### Adding New Data
1. Place new PDFs in `data/raw/`
2. Add JSON data to `data/raw/`
3. Rebuild the index:
   ```powershell
   docker-compose exec gather-foods-chatbot python -m training.cli ingest --pdf data/raw/ --json data/raw/
   docker-compose exec gather-foods-chatbot python -m training.cli chunk
   docker-compose exec gather-foods-chatbot python -m training.cli embed
   docker-compose exec gather-foods-chatbot python -m training.cli index
   ```

### Modifying the Model
- Replace `DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf` with any GGUF model
- Update the model path in `chatbot.py`
- Rebuild the container

### Customizing the Interface
- Edit the HTML/CSS in `chatbot.py` (around line 300)
- Modify the styling to match your brand
- Add additional features like file uploads or voice input

## 📈 Performance

### Resource Requirements
- **CPU**: 4+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Storage**: 2GB for model + data
- **Network**: Local only (no internet required after deployment)

### Optimization Tips
- **GPU Acceleration**: Set `n_gpu_layers=1` in `chatbot.py` if you have a GPU
- **Memory Tuning**: Adjust `n_threads` based on your CPU cores
- **Context Window**: Modify `n_ctx` for longer conversations

## 🔒 Security

### Data Protection
- **Encryption**: All data encrypted at rest
- **Access Control**: Local network access only
- **Audit Trail**: Complete conversation logging
- **Compliance**: Meets data sovereignty requirements

### Network Security
- **No External Calls**: Zero external API dependencies
- **Local Only**: Runs entirely within your network
- **Firewall Friendly**: No outbound connections required

## 🐛 Troubleshooting

### Common Issues

**Service won't start**
```powershell
# Check logs
docker-compose logs

# Verify model file exists
ls DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf

# Rebuild container
docker-compose down
docker-compose up --build -d
```

**Slow responses**
```powershell
# Check resource usage
docker stats

# Increase CPU threads in chatbot.py
# Set n_threads to match your CPU cores
```

**Memory issues**
```powershell
# Increase Docker memory limit
# Edit docker-compose.yml memory limits
```

### Health Check
```powershell
# Check service health
curl http://localhost:8000/api/health

# Expected response:
{
  "status": "healthy",
  "rag_available": true,
  "llm_available": true,
  "active_sessions": 0
}
```

## 📞 Support

For issues or questions:
1. Check the logs: `docker-compose logs -f`
2. Verify the health endpoint: http://localhost:8000/api/health
3. Ensure all prerequisites are met
4. Check resource usage and limits

## 🎉 Success!

You now have a **complete, data-sovereign chatbot** for Gather Foods that:
- ✅ Runs entirely on your infrastructure
- ✅ Protects all company and customer data
- ✅ Provides intelligent, contextual responses
- ✅ Honors Aboriginal heritage and culture
- ✅ Scales with your business needs

**Welcome to the future of secure, sovereign AI!** 🍃
