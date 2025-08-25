import { NextRequest, NextResponse } from 'next/server'
import ElevenLabs from 'elevenlabs-js'

// Initialize ElevenLabs client
const elevenlabs = new ElevenLabs({
  apiKey: process.env.ELEVENLABS_API_KEY || '',
})

// Premium voice options for Gather Foods AI
const VOICE_OPTIONS = {
  // Professional, warm, and culturally respectful voice
  primary: {
    voice_id: 'pNInz6obpgDQGcFmaJgB', // Adam - Professional male voice
    name: 'Adam',
    description: 'Professional, warm, and culturally respectful'
  },
  // Alternative voices for variety
  alternative: {
    voice_id: 'EXAVITQu4vr4xnSDxMaL', // Bella - Warm female voice
    name: 'Bella', 
    description: 'Warm, friendly, and approachable'
  },
  // Indigenous knowledge voice (if you have a specific voice)
  cultural: {
    voice_id: 'pNInz6obpgDQGcFmaJgB', // Using Adam as default
    name: 'Cultural Voice',
    description: 'Respectful and culturally aware'
  },
  // Additional voice options
  professional: {
    voice_id: '21m00Tcm4TlvDq8ikWAM', // Rachel - Professional female
    name: 'Rachel',
    description: 'Clear, professional, and articulate'
  },
  friendly: {
    voice_id: 'AZnzlk1XvdvUeBnXmlld', // Domi - Friendly and energetic
    name: 'Domi',
    description: 'Energetic and engaging'
  },
  calm: {
    voice_id: 'VR6AewLTigWG4xSOukaG', // Arnold - Calm and soothing
    name: 'Arnold',
    description: 'Calm, soothing, and trustworthy'
  },
  young: {
    voice_id: 'VR6AewLTigWG4xSOukaG', // Josh - Young and enthusiastic
    name: 'Josh',
    description: 'Young, enthusiastic, and modern'
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const { text, voice_type = 'primary' } = body

    if (!text) {
      return NextResponse.json(
        { error: 'Text is required' },
        { status: 400 }
      )
    }

    if (!process.env.ELEVENLABS_API_KEY) {
      return NextResponse.json(
        { error: 'ElevenLabs API key not configured' },
        { status: 500 }
      )
    }

    // Get voice configuration
    const voiceConfig = VOICE_OPTIONS[voice_type as keyof typeof VOICE_OPTIONS] || VOICE_OPTIONS.primary

    // Generate speech with ElevenLabs
    const audioBuffer = await elevenlabs.generate({
      text: text,
      voice_id: voiceConfig.voice_id,
      model_id: 'eleven_multilingual_v2', // Premium multilingual model
      voice_settings: {
        stability: 0.5,        // Balanced stability
        similarity_boost: 0.75, // Good voice consistency
        style: 0.0,            // Neutral style
        use_speaker_boost: true // Enhanced clarity
      }
    })

    // Convert to base64 for frontend
    const base64Audio = Buffer.from(audioBuffer).toString('base64')
    const dataUrl = `data:audio/mpeg;base64,${base64Audio}`

    return NextResponse.json({
      audio: dataUrl,
      voice: voiceConfig.name,
      duration: audioBuffer.length / 16000, // Approximate duration
      model: 'eleven_multilingual_v2'
    })

  } catch (error) {
    console.error('TTS Error:', error)
    
    return NextResponse.json(
      { 
        error: 'Failed to generate speech',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
}

export async function GET() {
  try {
    // Get available voices from ElevenLabs
    const voices = await elevenlabs.voices.getAll()
    
    return NextResponse.json({
      message: 'ElevenLabs TTS Service',
      available_voices: voices.length,
      configured_voices: Object.keys(VOICE_OPTIONS),
      voice_options: VOICE_OPTIONS
    })
  } catch (error) {
    return NextResponse.json({
      error: 'Failed to fetch voice information',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 })
  }
}
