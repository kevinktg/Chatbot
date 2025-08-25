'use client'

import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, MicOff, Send, Trash2, MessageSquare, Volume2, Settings } from 'lucide-react'

interface Message {
  id: string
  content: string
  role: 'user' | 'assistant'
  timestamp: Date
}

interface VoiceAssistantProps {
  onMessage: (message: string) => Promise<string>
}

type VoiceType = 'primary' | 'alternative' | 'cultural' | 'professional' | 'friendly' | 'calm' | 'young'

export default function VoiceAssistant({ onMessage }: VoiceAssistantProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: 'Welcome to Gather Foods AI! I\'m your voice-powered assistant. Ask me about our menu, dietary options, or company heritage. Click the microphone to start speaking!',
      role: 'assistant',
      timestamp: new Date()
    }
  ])
  const [isListening, setIsListening] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [inputMode, setInputMode] = useState<'voice' | 'text'>('voice')
  const [textInput, setTextInput] = useState('')
  const [recognition, setRecognition] = useState<SpeechRecognition | null>(null)
  const [voiceType, setVoiceType] = useState<VoiceType>('primary')
  const [showVoiceSettings, setShowVoiceSettings] = useState(false)
  const [isPlayingAudio, setIsPlayingAudio] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    // Initialize speech recognition
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      const recognition = new SpeechRecognition()
      
      recognition.continuous = false
      recognition.interimResults = false
      recognition.lang = 'en-US'
      
      recognition.onstart = () => {
        setIsListening(true)
      }
      
      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        handleUserMessage(transcript)
      }
      
      recognition.onend = () => {
        setIsListening(false)
      }
      
      recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error)
        setIsListening(false)
      }
      
      setRecognition(recognition)
    }
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const playElevenLabsAudio = async (text: string) => {
    try {
      setIsPlayingAudio(true)
      
      const response = await fetch('/api/tts', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text,
          voice_type: voiceType
        })
      })

      if (!response.ok) {
        throw new Error('Failed to generate speech')
      }

      const data = await response.json()
      
      // Create and play audio
      const audio = new Audio(data.audio)
      audioRef.current = audio
      
      audio.onended = () => {
        setIsPlayingAudio(false)
      }
      
      audio.onerror = () => {
        setIsPlayingAudio(false)
        console.error('Audio playback error')
      }
      
      await audio.play()
      
    } catch (error) {
      console.error('TTS Error:', error)
      setIsPlayingAudio(false)
      
      // Fallback to browser TTS
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text)
        utterance.rate = 0.9
        utterance.pitch = 1
        speechSynthesis.speak(utterance)
      }
    }
  }

  const stopAudio = () => {
    if (audioRef.current) {
      audioRef.current.pause()
      audioRef.current.currentTime = 0
      setIsPlayingAudio(false)
    }
  }

  const handleUserMessage = async (content: string) => {
    if (!content.trim()) return

    const userMessage: Message = {
      id: Date.now().toString(),
      content,
      role: 'user',
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setIsProcessing(true)

    try {
      const response = await onMessage(content)
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response,
        role: 'assistant',
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])

      // Play response with ElevenLabs if in voice mode
      if (inputMode === 'voice') {
        await playElevenLabsAudio(response)
      }
    } catch (error) {
      console.error('Error processing message:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'Sorry, I encountered an error. Please try again.',
        role: 'assistant',
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsProcessing(false)
    }
  }

  const startListening = () => {
    if (recognition && !isListening) {
      recognition.start()
    }
  }

  const stopListening = () => {
    if (recognition && isListening) {
      recognition.stop()
    }
  }

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (textInput.trim()) {
      handleUserMessage(textInput)
      setTextInput('')
    }
  }

  const clearMessages = () => {
    setMessages([
      {
        id: '1',
        content: 'Welcome to Gather Foods AI! I\'m your voice-powered assistant. Ask me about our menu, dietary options, or company heritage. Click the microphone to start speaking!',
        role: 'assistant',
        timestamp: new Date()
      }
    ])
  }

  const getVoiceDisplayName = (type: VoiceType) => {
    const names = {
      primary: 'Adam (Professional)',
      alternative: 'Bella (Friendly)',
      cultural: 'Cultural Voice',
      professional: 'Rachel (Clear)',
      friendly: 'Domi (Energetic)',
      calm: 'Arnold (Calm)',
      young: 'Josh (Modern)'
    }
    return names[type]
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-4 relative z-10">
      {/* Header */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-8"
      >
        <h1 className="text-4xl md:text-6xl font-bold text-gradient mb-2">
          🍃 Gather Foods AI
        </h1>
        <p className="text-xl text-white/80">
          Voice-Powered Indigenous Knowledge Assistant
        </p>
        <p className="text-sm text-white/60 mt-2">
          Powered by ElevenLabs Premium Voice Synthesis
        </p>
      </motion.div>

      {/* Main Interface */}
      <motion.div 
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        className="glass-effect rounded-3xl p-8 max-w-2xl w-full"
      >
        {/* Voice Visualization */}
        <div className="flex justify-center mb-6">
          <motion.div
            className="relative"
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <div 
              className={`voice-circle ${isListening ? 'listening' : ''} ${isPlayingAudio ? 'animate-glow' : ''}`}
              onClick={isListening ? stopListening : startListening}
            >
              <motion.div
                animate={isListening ? { scale: [1, 1.2, 1] } : {}}
                transition={{ duration: 1, repeat: Infinity }}
              >
                {isListening ? <MicOff size={32} /> : <Mic size={32} />}
              </motion.div>
            </div>
            
            {/* Audio playing indicator */}
            {isPlayingAudio && (
              <motion.div
                initial={{ opacity: 0, scale: 0 }}
                animate={{ opacity: 1, scale: 1 }}
                className="absolute -top-2 -right-2 bg-accent-500 rounded-full p-1"
              >
                <Volume2 size={16} className="text-white" />
              </motion.div>
            )}
          </motion.div>
        </div>

        {/* Status */}
        <motion.p 
          className="text-center text-white font-medium mb-6"
          animate={{ opacity: isListening ? 1 : 0.7 }}
        >
          {isListening ? 'Listening... Speak now!' : 
           isPlayingAudio ? 'Playing response...' : 
           'Click to start voice conversation'}
        </motion.p>

        {/* Controls */}
        <div className="flex justify-center gap-4 mb-6 flex-wrap">
          <motion.button
            className={`control-button ${inputMode === 'voice' ? 'active' : ''}`}
            onClick={() => setInputMode('voice')}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Mic className="w-4 h-4 mr-2" />
            Voice
          </motion.button>
          
          <motion.button
            className={`control-button ${inputMode === 'text' ? 'active' : ''}`}
            onClick={() => setInputMode('text')}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            Text
          </motion.button>
          
          <motion.button
            className="control-button"
            onClick={() => setShowVoiceSettings(!showVoiceSettings)}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Settings className="w-4 h-4 mr-2" />
            Voice
          </motion.button>
          
          <motion.button
            className="control-button"
            onClick={clearMessages}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Trash2 className="w-4 h-4 mr-2" />
            Clear
          </motion.button>
        </div>

        {/* Voice Settings */}
        <AnimatePresence>
          {showVoiceSettings && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-6 p-4 bg-white/10 backdrop-blur-sm rounded-2xl"
            >
              <h3 className="text-white font-medium mb-3">Voice Settings</h3>
              <div className="grid grid-cols-1 gap-2">
                {(['primary', 'alternative', 'cultural', 'professional', 'friendly', 'calm', 'young'] as VoiceType[]).map((type) => (
                  <motion.button
                    key={type}
                    className={`p-3 rounded-lg text-left transition-all ${
                      voiceType === type 
                        ? 'bg-primary-500/80 text-white' 
                        : 'bg-white/20 text-white hover:bg-white/30'
                    }`}
                    onClick={() => setVoiceType(type)}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    <div className="font-medium">{getVoiceDisplayName(type)}</div>
                    <div className="text-sm opacity-80">
                      {type === 'primary' && 'Professional, warm, and culturally respectful'}
                      {type === 'alternative' && 'Warm, friendly, and approachable'}
                      {type === 'cultural' && 'Respectful and culturally aware'}
                      {type === 'professional' && 'Clear, professional, and articulate'}
                      {type === 'friendly' && 'Energetic and engaging'}
                      {type === 'calm' && 'Calm, soothing, and trustworthy'}
                      {type === 'young' && 'Young, enthusiastic, and modern'}
                    </div>
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Chat Messages */}
        <div className="bg-white/10 backdrop-blur-sm rounded-2xl p-4 mb-6 max-h-80 overflow-y-auto">
          <AnimatePresence>
            {messages.map((message) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                className={`mb-3 ${message.role === 'user' ? 'text-right' : 'text-left'}`}
              >
                <div className={`message-bubble ${message.role}`}>
                  {message.content}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          
          {isProcessing && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-center text-white/70 italic"
            >
              AI is thinking...
            </motion.div>
          )}
          
          <div ref={messagesEndRef} />
        </div>

        {/* Text Input */}
        {inputMode === 'text' && (
          <motion.form
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            onSubmit={handleTextSubmit}
            className="flex gap-3"
          >
            <input
              type="text"
              value={textInput}
              onChange={(e) => setTextInput(e.target.value)}
              placeholder="Type your question here..."
              className="flex-1 px-4 py-3 rounded-full bg-white/20 backdrop-blur-sm text-white border border-white/30 focus:outline-none focus:border-primary-400 placeholder-white/50"
            />
            <motion.button
              type="submit"
              className="px-6 py-3 rounded-full bg-primary-500 text-white hover:bg-primary-600 transition-colors"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <Send size={20} />
            </motion.button>
          </motion.form>
        )}
      </motion.div>

      {/* Status Bar */}
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="fixed bottom-6 left-1/2 transform -translate-x-1/2 bg-black/70 text-white px-6 py-3 rounded-full backdrop-blur-sm text-sm"
      >
        🔒 Data-Sovereign AI • 🎤 ElevenLabs Premium Voice • Powered by Local DeepSeek Model
      </motion.div>
    </div>
  )
}
