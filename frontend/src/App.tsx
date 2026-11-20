import { Visualizer } from './components/Visualizer'
import { TelemetryStrip } from './components/TelemetryStrip'
import { TranscriptArea } from './components/TranscriptArea'
import { CommandBar } from './components/CommandBar'
import { ExecutionDrawer } from './components/ExecutionDrawer'
import { useMockController } from './hooks/useMockController'
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
    state,
    isMicActive,
    telemetry,
    dialogue,
    logs,
    isDrawerOpen,
    setIsDrawerOpen,
    toggleMic,
    executePipeline,
    selectState,
    clearLogs,
  } = useMockController()

  const currentBadge = STATE_BADGES[state]

  return (
    <div className="relative flex min-h-screen flex-col items-center justify-between bg-[#0b0e14] px-4 py-6 text-slate-100 selection:bg-cyan-500 selection:text-black">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,rgba(56,189,248,0.06),rgba(0,0,0,0))]" />

      <main className="relative z-10 flex w-full max-w-3xl flex-col gap-4">
        <header className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/[0.08] bg-slate-900/80 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.08)]">
              <span className="font-mono text-sm font-bold tracking-tight text-cyan-400">G</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-sm font-semibold tracking-tight text-white">Gipsy</h1>
                <span className="font-mono text-[10px] text-slate-500">v0.1.0</span>
              </div>
              <p className="text-[11px] text-slate-400">Local Voice & OS Control Surface</p>
            </div>
          </div>

          <div
            className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 font-mono text-[11px] transition-colors duration-200 ${currentBadge.border}`}
          >
            <span className={`h-2 w-2 rounded-full ${currentBadge.dot}`} />
            <span className={`font-medium ${currentBadge.text}`}>{currentBadge.label}</span>
          </div>
        </header>

        <TelemetryStrip
          telemetry={telemetry}
          onToggleDrawer={() => setIsDrawerOpen(!isDrawerOpen)}
          isDrawerOpen={isDrawerOpen}
          logCount={logs.length}
        />

        <div className="relative rounded-2xl border border-white/[0.06] bg-slate-900/40 p-3 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04),0_12px_32px_-8px_rgba(0,0,0,0.6)] backdrop-blur-xl">
          <Visualizer state={state} />

          <div className="mt-2 text-center">
            <span className="font-mono text-[11px] uppercase tracking-wider text-slate-400">
              Core State: <span className="font-semibold text-slate-200">{state.replace('_', ' ')}</span>
            </span>
          </div>
        </div>

        <TranscriptArea dialogue={dialogue} />

        <CommandBar
          state={state}
          isMicActive={isMicActive}
          onToggleMic={toggleMic}
          onSubmitCommand={executePipeline}
          onSelectState={selectState}
        />

        <ExecutionDrawer
          isOpen={isDrawerOpen}
          logs={logs}
          onClose={() => setIsDrawerOpen(false)}
          onClear={clearLogs}
        />
      </main>

      <footer className="relative z-10 mt-6 flex items-center justify-between text-[11px] text-slate-400">
        <span className="font-mono">Decoupled Architecture • React + Tailwind CSS v4</span>
        <span className="font-mono">Port 5173 ⇄ 8000</span>
      </footer>
    </div>
  )
}
