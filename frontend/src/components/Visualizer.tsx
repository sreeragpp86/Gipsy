import { useEffect, useRef } from 'react'
import type { AssistantState } from '../types/hud'

interface VisualizerProps {
  state: AssistantState
  audioAmplitude?: number
}

interface StateStyle {
  r: number
  g: number
  b: number
  amplitude: number
  frequency: number
  speed: number
  ringCount: number
  coreScale: number
}

const STATE_CONFIGS: Record<AssistantState, StateStyle> = {
  IDLE: {
    r: 148,
    g: 163,
    b: 184,
    amplitude: 0.15,
    frequency: 2.0,
    speed: 0.015,
    ringCount: 2,
    coreScale: 0.7,
  },
  LISTENING: {
    r: 56,
    g: 189,
    b: 248,
    amplitude: 0.65,
    frequency: 4.5,
    speed: 0.04,
    ringCount: 4,
    coreScale: 1.05,
  },
  PROCESSING: {
    r: 167,
    g: 139,
    b: 250,
    amplitude: 0.4,
    frequency: 6.0,
    speed: 0.06,
    ringCount: 3,
    coreScale: 0.9,
  },
  EXECUTING_TOOL: {
    r: 251,
    g: 191,
    b: 36,
    amplitude: 0.3,
    frequency: 8.0,
    speed: 0.03,
    ringCount: 3,
    coreScale: 0.85,
  },
  SPEAKING: {
    r: 52,
    g: 211,
    b: 153,
    amplitude: 0.8,
    frequency: 3.2,
    speed: 0.05,
    ringCount: 4,
    coreScale: 1.15,
  },
}

function lerp(start: number, end: number, factor: number): number {
  return start + (end - start) * factor
}

export function Visualizer({ state, audioAmplitude = 0 }: VisualizerProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const currentRef = useRef<StateStyle>({ ...STATE_CONFIGS.IDLE })
  const phaseRef = useRef<number>(0)
  const amplitudeRef = useRef<number>(audioAmplitude)

  useEffect(() => {
    amplitudeRef.current = audioAmplitude
  }, [audioAmplitude])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animationFrameId: number

    const handleResize = () => {
      const dpr = window.devicePixelRatio || 1
      const rect = canvas.getBoundingClientRect()
      canvas.width = rect.width * dpr
      canvas.height = rect.height * dpr
      ctx.resetTransform()
      ctx.scale(dpr, dpr)
    }

    handleResize()
    window.addEventListener('resize', handleResize)

    const render = () => {
      const target = STATE_CONFIGS[state]
      const current = currentRef.current
      const lerpSpeed = 0.08

      const liveAmp = state === 'SPEAKING' && amplitudeRef.current > 0
        ? Math.max(target.amplitude, amplitudeRef.current * 1.5)
        : target.amplitude

      current.r = lerp(current.r, target.r, lerpSpeed)
      current.g = lerp(current.g, target.g, lerpSpeed)
      current.b = lerp(current.b, target.b, lerpSpeed)
      current.amplitude = lerp(current.amplitude, liveAmp, lerpSpeed)
      current.frequency = lerp(current.frequency, target.frequency, lerpSpeed)
      current.speed = lerp(current.speed, target.speed, lerpSpeed)
      current.coreScale = lerp(current.coreScale, target.coreScale, lerpSpeed)

      phaseRef.current += current.speed

      const rect = canvas.getBoundingClientRect()
      const width = rect.width
      const height = rect.height
      const centerX = width / 2
      const centerY = height / 2
      const baseRadius = Math.min(width, height) * 0.22

      ctx.clearRect(0, 0, width, height)

      const colorBase = `${Math.round(current.r)}, ${Math.round(current.g)}, ${Math.round(current.b)}`

      const gradient = ctx.createRadialGradient(
        centerX,
        centerY,
        baseRadius * 0.2,
        centerX,
        centerY,
        baseRadius * 1.8
      )
      gradient.addColorStop(0, `rgba(${colorBase}, 0.18)`)
      gradient.addColorStop(0.5, `rgba(${colorBase}, 0.05)`)
      gradient.addColorStop(1, 'rgba(0, 0, 0, 0)')

      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.arc(centerX, centerY, baseRadius * 1.8, 0, Math.PI * 2)
      ctx.fill()

      for (let ring = 0; ring < target.ringCount; ring++) {
        const ringOffset = ring * 0.4
        const ringRadius = baseRadius * (0.8 + ring * 0.18) * current.coreScale
        const ringAlpha = (0.28 / (ring + 1)) * (0.8 + current.amplitude * 0.4)

        ctx.strokeStyle = `rgba(${colorBase}, ${ringAlpha})`
        ctx.lineWidth = 1.5
        ctx.beginPath()

        const segments = 120
        for (let i = 0; i <= segments; i++) {
          const theta = (i / segments) * Math.PI * 2
          const wave1 = Math.sin(theta * current.frequency + phaseRef.current + ringOffset)
          const wave2 = Math.cos(theta * (current.frequency * 0.5) - phaseRef.current * 0.7)
          const mod = 1 + (wave1 * 0.6 + wave2 * 0.4) * current.amplitude * 0.25
          const r = ringRadius * mod

          const x = centerX + Math.cos(theta) * r
          const y = centerY + Math.sin(theta) * r

          if (i === 0) {
            ctx.moveTo(x, y)
          } else {
            ctx.lineTo(x, y)
          }
        }
        ctx.closePath()
        ctx.stroke()
      }

      const coreRadius = baseRadius * 0.42 * current.coreScale
      const corePulse = Math.sin(phaseRef.current * 1.8) * 0.06

      const innerGradient = ctx.createRadialGradient(
        centerX,
        centerY,
        0,
        centerX,
        centerY,
        coreRadius * (1 + corePulse)
      )
      innerGradient.addColorStop(0, `rgba(${colorBase}, 0.85)`)
      innerGradient.addColorStop(0.4, `rgba(${colorBase}, 0.35)`)
      innerGradient.addColorStop(1, `rgba(${colorBase}, 0)`)

      ctx.fillStyle = innerGradient
      ctx.beginPath()
      ctx.arc(centerX, centerY, coreRadius * (1 + corePulse), 0, Math.PI * 2)
      ctx.fill()

      ctx.strokeStyle = `rgba(${colorBase}, 0.7)`
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.arc(centerX, centerY, coreRadius * 0.45, 0, Math.PI * 2)
      ctx.stroke()

      animationFrameId = requestAnimationFrame(render)
    }

    render()

    return () => {
      window.removeEventListener('resize', handleResize)
      cancelAnimationFrame(animationFrameId)
    }
  }, [state])

  return (
    <div className="relative flex h-48 w-full items-center justify-center overflow-hidden rounded-2xl bg-slate-950/40">
      <canvas
        ref={canvasRef}
        className="h-full w-full max-w-md touch-none"
      />
    </div>
  )
}
