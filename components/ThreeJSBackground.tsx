'use client'

import { useEffect, useRef } from 'react'
import * as THREE from 'three'

interface ThreeJSBackgroundProps {
  isListening: boolean
}

export default function ThreeJSBackground({ isListening }: ThreeJSBackgroundProps) {
  const mountRef = useRef<HTMLDivElement>(null)
  const sceneRef = useRef<THREE.Scene | null>(null)
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null)
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null)
  const particlesRef = useRef<THREE.Points | null>(null)
  const voiceWavesRef = useRef<THREE.Mesh[]>([])
  const animationIdRef = useRef<number>()

  useEffect(() => {
    if (!mountRef.current) return

    // Scene setup
    const scene = new THREE.Scene()
    sceneRef.current = scene

    // Camera setup
    const camera = new THREE.PerspectiveCamera(
      75,
      window.innerWidth / window.innerHeight,
      0.1,
      1000
    )
    camera.position.z = 5
    cameraRef.current = camera

    // Renderer setup
    const renderer = new THREE.WebGLRenderer({ 
      antialias: true, 
      alpha: true 
    })
    renderer.setSize(window.innerWidth, window.innerHeight)
    renderer.setClearColor(0x000000, 0)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    mountRef.current.appendChild(renderer.domElement)
    rendererRef.current = renderer

    // Create floating particles
    const particleCount = 150
    const geometry = new THREE.BufferGeometry()
    const positions = new Float32Array(particleCount * 3)
    const colors = new Float32Array(particleCount * 3)
    const sizes = new Float32Array(particleCount)

    for (let i = 0; i < particleCount * 3; i += 3) {
      positions[i] = (Math.random() - 0.5) * 20
      positions[i + 1] = (Math.random() - 0.5) * 20
      positions[i + 2] = (Math.random() - 0.5) * 20

      colors[i] = Math.random() * 0.5 + 0.5
      colors[i + 1] = Math.random() * 0.5 + 0.5
      colors[i + 2] = Math.random() * 0.5 + 0.5

      sizes[i / 3] = Math.random() * 0.1 + 0.05
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3))
    geometry.setAttribute('size', new THREE.BufferAttribute(sizes, 1))

    const particleMaterial = new THREE.PointsMaterial({
      size: 0.05,
      vertexColors: true,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
    })

    const particles = new THREE.Points(geometry, particleMaterial)
    scene.add(particles)
    particlesRef.current = particles

    // Create voice waves
    const waveCount = 4
    for (let i = 0; i < waveCount; i++) {
      const geometry = new THREE.RingGeometry(0.5 + i * 0.3, 0.6 + i * 0.3, 32)
      const material = new THREE.MeshBasicMaterial({
        color: 0x22c55e,
        transparent: true,
        opacity: 0.3,
        side: THREE.DoubleSide,
      })

      const wave = new THREE.Mesh(geometry, material)
      wave.visible = false
      voiceWavesRef.current.push(wave)
      scene.add(wave)
    }

    // Animation loop
    const animate = () => {
      animationIdRef.current = requestAnimationFrame(animate)

      // Rotate particles
      if (particlesRef.current) {
        particlesRef.current.rotation.x += 0.001
        particlesRef.current.rotation.y += 0.002
      }

      // Animate voice waves
      if (isListening) {
        voiceWavesRef.current.forEach((wave, index) => {
          wave.visible = true
          const scale = 1 + Math.sin(Date.now() * 0.003 + index) * 0.2
          wave.scale.setScalar(scale)
          wave.material.opacity = 0.3 + Math.sin(Date.now() * 0.002 + index) * 0.2
          wave.material.color.setHex(isListening ? 0xef4444 : 0x22c55e)
        })
      } else {
        voiceWavesRef.current.forEach((wave) => {
          wave.visible = false
        })
      }

      renderer.render(scene, camera)
    }

    animate()

    // Handle window resize
    const handleResize = () => {
      if (!cameraRef.current || !rendererRef.current) return

      cameraRef.current.aspect = window.innerWidth / window.innerHeight
      cameraRef.current.updateProjectionMatrix()
      rendererRef.current.setSize(window.innerWidth, window.innerHeight)
    }

    window.addEventListener('resize', handleResize)

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize)
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current)
      }
      if (mountRef.current && rendererRef.current) {
        mountRef.current.removeChild(rendererRef.current.domElement)
      }
      if (rendererRef.current) {
        rendererRef.current.dispose()
      }
    }
  }, [])

  return (
    <div 
      ref={mountRef} 
      className="fixed inset-0 z-0 pointer-events-none"
    />
  )
}
