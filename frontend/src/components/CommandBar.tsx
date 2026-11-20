import { useState, type FormEvent } from 'react'
import { ArrowUp, Mic, MicOff } from 'lucide-react'
import type { AssistantState } from '../types/hud'

interface CommandBarProps {
  state: AssistantState
  isMicActive: boolean
  onToggleMic: () => void
  onSubmitCommand: (text: string) => void
  onSelectState: (state: AssistantState) => void
}

const AVAILABLE_STATES: AssistantState[] = [
  'IDLE',
  'LISTENING',
  'PROCESSING',
  'EXECUTING_TOOL',
  'SPEAKING',
]

export function CommandBar({
  state,
  isMicActive,
  onToggleMic,
  onSubmitCommand,
  onSelectState,
}: CommandBarProps) {
  const [input, setInput] = useState('')

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed) return
    onSubmitCommand(trimmed)
    setInput('')
  }

  return (
    <div className="flex w-full flex-col gap-3">
      <form
        onSubmit={handleSubmit}
        className="group relative flex items-center gap-2 rounded-2xl border border-white/[0.08] bg-slate-900/80 p-1.5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.06),0_8px_24px_-4px_rgba(0,0,0,0.5)] backdrop-blur-xl transition-all duration-200 focus-within:border-cyan-500/40 focus-within:shadow-[0_0_0_1px_rgba(6,182,212,0.2),0_8px_24px_-4px_rgba(0,0,0,0.5)]"
      >
        <button
          type="button"
          onClick={onToggleMic}
          aria-label={isMicActive ? 'Mute microphone' : 'Activate microphone'}
          className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl transition-all duration-150 active:scale-95 ${
            isMicActive
              ? 'bg-rose-500/15 text-rose-300 shadow-[inset_0_0_0_1px_rgba(244,63,94,0.3)] animate-pulse'
              : 'bg-white/[0.04] text-slate-300 hover:bg-white/[0.08] hover:text-white'
          }`}
        >
          {isMicActive ? <Mic className="h-5 w-5" /> : <MicOff className="h-5 w-5" />}
        </button>

        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask Gipsy or give an OS command..."
          className="h-11 w-full bg-transparent px-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none"
        />

        <button
          type="submit"
          disabled={!input.trim()}
          aria-label="Send command"
          className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-cyan-500 text-slate-950 transition-all duration-150 enabled:hover:bg-cyan-400 enabled:active:scale-95 disabled:bg-white/[0.04] disabled:text-slate-600 disabled:cursor-not-allowed"
        >
          <ArrowUp className="h-5 w-5 stroke-[2.5]" />
        </button>
      </form>

      <div className="flex flex-wrap items-center justify-center gap-1.5 py-1">
        <span className="mr-1 text-[10px] font-medium uppercase tracking-wider text-slate-500">
          State Simulator:
        </span>
        {AVAILABLE_STATES.map((s) => {
          const isActive = state === s
          return (
            <button
              key={s}
              type="button"
              onClick={() => onSelectState(s)}
              className={`rounded-lg border px-2.5 py-1 font-mono text-[10px] uppercase tracking-wider transition-all duration-150 active:scale-95 ${
                isActive
                  ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-300 shadow-[0_0_8px_rgba(6,182,212,0.15)]'
                  : 'border-white/[0.05] bg-slate-950/30 text-slate-400 hover:border-white/10 hover:text-slate-300'
              }`}
            >
              {s.replace('_', ' ')}
            </button>
          )
        })}
      </div>
    </div>
  )
}
