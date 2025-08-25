'use client'

import { useState } from 'react'
import ThreeJSBackground from '@/components/ThreeJSBackground'
import VoiceAssistant from '@/components/VoiceAssistant'

export default function Home() {
  const [isListening, setIsListening] = useState(false)

  const handleMessage = async (message: string): Promise<string> => {
    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          session_id: 'nextjs-session'
        })
      })

      if (!response.ok) {
        throw new Error('Failed to get response')
      }

      const data = await response.json()
      return data.response
    } catch (error) {
      console.error('Error:', error)
      return 'Sorry, I encountered an error. Please try again.'
    }
  }

  return (
    <main className="relative min-h-screen overflow-hidden">
      {/* Three.js Background */}
      <ThreeJSBackground isListening={isListening} />
      
      {/* Voice Assistant */}
      <VoiceAssistant onMessage={handleMessage} />
    </main>
  )
}
