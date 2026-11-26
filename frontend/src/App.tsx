import { useEffect, useState } from 'react'
import { Minimize2, Pin, PinOff } from 'lucide-react'
import { Visualizer } from './components/Visualizer'
import { TelemetryStrip } from './components/TelemetryStrip'
import { TranscriptArea } from './components/TranscriptArea'
import { CommandBar } from './components/CommandBar'
import { ExecutionDrawer } from './components/ExecutionDrawer'
import { PillView } from './components/PillView'
import { AdminAuthModal } from './components/AdminAuthModal'
import { useGipsySocket } from './hooks/useGipsySocket'
import { startWindowDrag, useTauriWindow } from './hooks/useTauriWindow'
import type { AssistantState } from './types/hud'

const STATE_BADGES: Record<AssistantState, { label: string; dot: string; text: string; border: string }> = {
  IDLE: {
    label: 'Idle • Standby',
    dot: 'bg-slate-400',
    text: 'text-slate-300',
    border: 'border-slate-700/40 bg-slate-800/30',
  },
  LISTENING: {
    label: 'Listening • Audio In',
    dot: 'bg-sky-400 shadow-[0_0_8px_#38bdf8]',
    text: 'text-sky-300',
    border: 'border-sky-500/30 bg-sky-500/10',
  },
  PROCESSING: {
    label: 'Processing • Reasoning',
    dot: 'bg-purple-400 shadow-[0_0_8px_#c084fc] animate-pulse',
    text: 'text-purple-300',
    border: 'border-purple-500/30 bg-purple-500/10',
  },
  EXECUTING_TOOL: {
    label: 'Executing • OS Tool',
    dot: 'bg-amber-400 shadow-[0_0_8px_#fbbf24] animate-pulse',
    text: 'text-amber-300',
    border: 'border-amber-500/30 bg-amber-500/10',
  },
  SPEAKING: {
    label: 'Speaking • Voice Out',
    dot: 'bg-emerald-400 shadow-[0_0_8px_#34d399]',
    text: 'text-emerald-300',
    border: 'border-emerald-500/30 bg-emerald-500/10',
  },
}

export function App() {
  const {
    status,
    assistantState,
    isMicActive,
    isDrawerOpen,
    setIsDrawerOpen,
    audioAmplitude,
    adminChallenge,
    telemetry,
    dialogue,
    logs,
    sendCommand,
    toggleMic,
    clearLogs,
    submitAdminAuth,
    cancelAdminAuth,
  } = useGipsySocket()

  const { hudMode, setHudMode } = useTauriWindow()
  const [isPinned, setIsPinned] = useState(false)
  const [expandSource, setExpandSource] = useState<'manual' | 'auto'>('manual')
  const [isInputFocused, setIsInputFocused] = useState(false)
  const [hasDraftText, setHasDraftText] = useState(false)

  useEffect(() => {
    if (adminChallenge || assistantState !== 'IDLE') {
      setHudMode('expanded')
      setExpandSource('auto')
      return
    }

    if (
      hudMode !== 'expanded' ||
      isPinned ||
      expandSource === 'manual' ||
      isInputFocused ||
      hasDraftText ||
      isDrawerOpen
    ) {
      return
    }

    const timer = setTimeout(() => {
      setHudMode('pill')
    }, 8000)

    return () => clearTimeout(timer)
  }, [
    adminChallenge,
    assistantState,
    isPinned,
    hudMode,
    expandSource,
    isInputFocused,
    hasDraftText,
    isDrawerOpen,
    setHudMode,
  ])

  const currentBadge = STATE_BADGES[assistantState]

  if (hudMode === 'pill') {
    return (
      <div
        data-tauri-drag-region
        onMouseDown={startWindowDrag}
        className="flex h-screen w-screen items-center justify-center bg-transparent p-0 select-none cursor-grab active:cursor-grabbing"
      >
        <PillView
          state={assistantState}
          audioAmplitude={audioAmplitude}
          isMicActive={isMicActive}
          connectionStatus={status}
          onToggleMic={toggleMic}
          onExpand={() => {
            setExpandSource('manual')
            setHudMode('expanded')
          }}
        />
      </div>
    )
  }

  return (
    <div className="relative flex h-screen w-screen flex-col justify-between overflow-hidden bg-[#0b0e14]/85 backdrop-blur-2xl p-4 text-slate-100 selection:bg-cyan-500 selection:text-black">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,rgba(56,189,248,0.06),rgba(0,0,0,0))]" />

      <header
        data-tauri-drag-region
        onMouseDown={startWindowDrag}
        className="relative z-20 mb-2 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between select-none cursor-grab active:cursor-grabbing shrink-0"
      >
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/[0.08] bg-slate-900/80 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.08)]">
            <span className="font-mono text-sm font-bold tracking-tight text-cyan-400">G</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-semibold tracking-tight text-white">Gipsy</h1>
              <span className="font-mono text-[10px] text-slate-500">v0.1.0</span>
              <span
                className={`inline-block h-1.5 w-1.5 rounded-full ${
                  status === 'connected'
                    ? 'bg-emerald-400 shadow-[0_0_6px_#34d399]'
                    : status === 'connecting'
                    ? 'bg-amber-400 animate-pulse'
                    : 'bg-rose-500'
                }`}
                title={`WebSocket ${status}`}
              />
            </div>
            <p className="text-[11px] text-slate-400">Local Voice & OS Control Surface</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div
            className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-[11px] transition-colors duration-200 ${currentBadge.border}`}
          >
            <span className={`h-2 w-2 rounded-full ${currentBadge.dot}`} />
            <span className={`font-medium ${currentBadge.text}`}>{currentBadge.label}</span>
          </div>

          <button
            type="button"
            onClick={() => setIsPinned(!isPinned)}
            className={`flex h-7 w-7 items-center justify-center rounded-lg border transition-colors ${
              isPinned
                ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-300'
                : 'border-white/[0.06] bg-slate-900/60 text-slate-400 hover:text-slate-200'
            }`}
            title={isPinned ? 'Unpin (auto-collapses when idle)' : 'Pin (keep expanded)'}
          >
            {isPinned ? <PinOff size={13} /> : <Pin size={13} />}
          </button>

          <button
            type="button"
            onClick={() => {
              setHudMode('pill')
              setExpandSource('manual')
            }}
            className="flex h-7 w-7 items-center justify-center rounded-lg border border-white/[0.06] bg-slate-900/60 text-slate-400 transition-colors hover:text-slate-200"
            title="Minimize to Notch Pill"
          >
            <Minimize2 size={13} />
          </button>
        </div>
      </header>

      <div className="relative z-10 flex flex-1 flex-col gap-3 overflow-y-auto overflow-x-hidden pr-1 pb-1">
        <TelemetryStrip
          telemetry={telemetry}
          onToggleDrawer={() => setIsDrawerOpen(!isDrawerOpen)}
          isDrawerOpen={isDrawerOpen}
          logCount={logs.length}
        />

        <div className="relative rounded-2xl border border-white/[0.06] bg-slate-900/40 p-2.5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04),0_12px_32px_-8px_rgba(0,0,0,0.6)] backdrop-blur-xl">
          <Visualizer state={assistantState} audioAmplitude={audioAmplitude} />

          <div className="mt-2 text-center">
            <span className="font-mono text-[11px] uppercase tracking-wider text-slate-400">
              Core State: <span className="font-semibold text-slate-200">{assistantState.replace('_', ' ')}</span>
            </span>
          </div>
        </div>

        <TranscriptArea dialogue={dialogue} />

        <ExecutionDrawer
          isOpen={isDrawerOpen}
          logs={logs}
          onClose={() => setIsDrawerOpen(false)}
          onClear={clearLogs}
        />
      </div>

      <div className="relative z-20 mt-2.5 shrink-0">
        <CommandBar
          isMicActive={isMicActive}
          onToggleMic={toggleMic}
          onSubmitCommand={(text) => {
            sendCommand(text)
            setHasDraftText(false)
          }}
          onFocusChange={(focused) => {
            setIsInputFocused(focused)
            if (focused) {
              setExpandSource('manual')
            }
          }}
          onInputChange={(text) => {
            const hasText = text.trim().length > 0
            setHasDraftText(hasText)
            if (hasText) {
              setExpandSource('manual')
            }
          }}
        />
      </div>

      {adminChallenge && (
        <AdminAuthModal
          challenge={adminChallenge}
          onSubmit={submitAdminAuth}
          onCancel={cancelAdminAuth}
        />
      )}

      <footer className="relative z-10 mt-2 flex items-center justify-between text-[10px] text-slate-500 shrink-0">
        <span className="font-mono">Project Gipsy • Local Voice & OS Surface</span>
        <span className="font-mono">127.0.0.1:8000</span>
      </footer>
    </div>
  )
}
