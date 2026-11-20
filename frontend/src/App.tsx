import { useState, useEffect } from 'react'

interface HealthResponse {
  status: string
  version: string
  timestamp: string
}

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected')

  useEffect(() => {
    fetch('http://localhost:8000/health')
      .then((res) => res.json())
      .then((data: HealthResponse) => setHealth(data))
      .catch(() => setHealth(null))

    const socket = new WebSocket('ws://localhost:8000/ws')

    socket.onopen = () => {
      setWsStatus('connected')
    }

    socket.onclose = () => {
      setWsStatus('disconnected')
    }

    socket.onerror = () => {
      setWsStatus('disconnected')
    }

    return () => {
      socket.close()
    }
  }, [])

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-6 selection:bg-cyan-500 selection:text-black">
      <div className="w-full max-w-2xl rounded-2xl border border-slate-800 bg-slate-900/60 p-8 shadow-2xl backdrop-blur-xl">
        <header className="flex items-center justify-between border-b border-slate-800 pb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="inline-block h-3 w-3 rounded-full bg-cyan-400 shadow-[0_0_12px_#22d3ee] animate-pulse" />
              <h1 className="text-2xl font-bold tracking-tight text-white">Project Gipsy</h1>
            </div>
            <p className="mt-1 text-sm text-slate-400">Local Voice Assistant & OS Controller</p>
          </div>
          <span className="rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs font-medium text-cyan-300">
            HUD v0.1.0
          </span>
        </header>

        <section className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="rounded-xl border border-slate-800/80 bg-slate-950/50 p-4">
            <span className="text-xs uppercase tracking-wider text-slate-400">Backend Health</span>
            <div className="mt-2 flex items-center gap-2">
              <span
                className={`h-2.5 w-2.5 rounded-full ${
                  health?.status === 'ok' ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]' : 'bg-amber-400'
                }`}
              />
              <span className="font-mono text-sm font-semibold text-slate-200">
                {health?.status === 'ok' ? 'Online' : 'Offline / Standby'}
              </span>
            </div>
            {health && (
              <p className="mt-2 font-mono text-xs text-slate-400">
                v{health.version} • {new Date(health.timestamp).toLocaleTimeString()}
              </p>
            )}
          </div>

          <div className="rounded-xl border border-slate-800/80 bg-slate-950/50 p-4">
            <span className="text-xs uppercase tracking-wider text-slate-400">WebSocket Link</span>
            <div className="mt-2 flex items-center gap-2">
              <span
                className={`h-2.5 w-2.5 rounded-full ${
                  wsStatus === 'connected'
                    ? 'bg-emerald-400 shadow-[0_0_8px_#34d399]'
                    : wsStatus === 'connecting'
                    ? 'bg-yellow-400'
                    : 'bg-rose-400'
                }`}
              />
              <span className="font-mono text-sm font-semibold text-slate-200 uppercase">
                {wsStatus}
              </span>
            </div>
            <p className="mt-2 font-mono text-xs text-slate-400">ws://localhost:8000/ws</p>
          </div>
        </section>

        <footer className="mt-6 flex items-center justify-between border-t border-slate-800/80 pt-4 text-xs text-slate-400">
          <span>Decoupled Architecture</span>
          <span>FastAPI + Vite + Tailwind CSS v4</span>
        </footer>
      </div>
    </main>
  )
}
