import { Maximize2, Mic, MicOff } from 'lucide-react'
import type { AssistantState } from '../types/hud'

interface PillViewProps {
  state: AssistantState
  audioAmplitude: number
  isMicActive: boolean
  connectionStatus: 'connected' | 'connecting' | 'disconnected'
  onToggleMic: () => void
  onExpand: () => void
}

const STATE_DOTS: Record<AssistantState, { dot: string; label: string }> = {
  IDLE: { dot: 'bg-slate-400', label: 'Standby' },
  LISTENING: { dot: 'bg-sky-400 shadow-[0_0_8px_#38bdf8]', label: 'Listening' },
  PROCESSING: { dot: 'bg-purple-400 shadow-[0_0_8px_#c084fc] animate-pulse', label: 'Thinking' },
  EXECUTING_TOOL: { dot: 'bg-amber-400 shadow-[0_0_8px_#fbbf24] animate-pulse', label: 'Executing' },
  SPEAKING: { dot: 'bg-emerald-400 shadow-[0_0_8px_#34d399]', label: 'Speaking' },
}

export function PillView({
  state,
  audioAmplitude,
  isMicActive,
  connectionStatus,
  onToggleMic,
  onExpand,
}: PillViewProps) {
  const current = STATE_DOTS[state]

  return (
    <div
      data-tauri-drag-region
      className="flex h-14 w-full max-w-[280px] select-none items-center justify-between rounded-full border border-white/[0.08] bg-[#0b0e14]/90 px-3.5 shadow-[0_8px_32px_rgba(0,0,0,0.6),inset_0_1px_0_0_rgba(255,255,255,0.06)] backdrop-blur-2xl transition-all duration-300"
    >
      <div className="flex items-center gap-2.5">
        <div className="relative flex h-7 w-7 items-center justify-center rounded-full bg-slate-900/90 border border-white/[0.08]">
          <span className={`h-2 w-2 rounded-full transition-colors duration-300 ${current.dot}`} />
          {connectionStatus === 'connected' && (
            <span className="absolute -bottom-0.5 -right-0.5 h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_4px_#34d399]" />
          )}
        </div>

        <div className="flex flex-col">
          <div className="flex items-center gap-1.5">
            <span className="font-mono text-xs font-semibold text-slate-200">Gipsy</span>
            <span className="text-[10px] text-slate-500">•</span>
            <span className="font-mono text-[10px] text-slate-400">{current.label}</span>
          </div>

          <div className="flex h-2 items-center gap-0.5">
            {[0.15, 0.4, 0.7, 0.35, 0.2].map((base, i) => {
              const height =
                state === 'SPEAKING' || (state === 'LISTENING' && audioAmplitude > 0.05)
                  ? Math.max(3, Math.min(10, (audioAmplitude || 0.4) * 10 * (base + 0.3)))
                  : 3
              return (
                <span
                  key={i}
                  className={`w-0.5 rounded-full transition-all duration-75 ${
                    state === 'SPEAKING'
                      ? 'bg-emerald-400'
                      : state === 'LISTENING'
                      ? 'bg-sky-400'
                      : 'bg-slate-600'
                  }`}
                  style={{ height: `${height}px` }}
                />
              )
            })}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation()
            onToggleMic()
          }}
          className={`flex h-7 w-7 items-center justify-center rounded-full border transition-all duration-200 ${
            isMicActive
              ? 'border-sky-500/40 bg-sky-500/15 text-sky-400 shadow-[0_0_8px_rgba(56,189,248,0.2)]'
              : 'border-white/[0.06] bg-slate-800/40 text-slate-400 hover:border-white/[0.12] hover:text-slate-200'
          }`}
          title={isMicActive ? 'Mute microphone' : 'Unmute microphone'}
        >
          {isMicActive ? <Mic size={12} /> : <MicOff size={12} />}
        </button>

        <button
          type="button"
          onClick={onExpand}
          className="flex h-7 w-7 items-center justify-center rounded-full border border-white/[0.06] bg-slate-800/40 text-slate-400 transition-all duration-200 hover:border-white/[0.12] hover:text-slate-200"
          title="Expand HUD"
        >
          <Maximize2 size={12} />
        </button>
      </div>
    </div>
  )
}
