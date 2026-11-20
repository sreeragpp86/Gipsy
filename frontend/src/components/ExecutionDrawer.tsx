import { Trash2, X } from 'lucide-react'
import type { LogEntry } from '../types/hud'

interface ExecutionDrawerProps {
  isOpen: boolean
  logs: LogEntry[]
  onClose: () => void
  onClear: () => void
}

export function ExecutionDrawer({
  isOpen,
  logs,
  onClose,
  onClear,
}: ExecutionDrawerProps) {
  if (!isOpen) return null

  return (
    <div className="w-full overflow-hidden rounded-2xl border border-white/[0.08] bg-slate-900/90 shadow-2xl backdrop-blur-2xl transition-all duration-200">
      <div className="flex items-center justify-between border-b border-white/[0.06] px-4 py-2.5">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-semibold text-slate-200 uppercase tracking-wider">
            System & Execution Events
          </span>
          <span className="rounded bg-white/[0.08] px-1.5 py-0.5 font-mono text-[10px] text-slate-400">
            {logs.length}
          </span>
        </div>

        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={onClear}
            disabled={logs.length === 0}
            className="flex items-center gap-1 rounded-md px-2 py-1 text-[11px] text-slate-400 transition-colors hover:bg-white/[0.06] hover:text-rose-300 disabled:opacity-40"
          >
            <Trash2 className="h-3 w-3" />
            <span>Clear</span>
          </button>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md p-1 text-slate-400 transition-colors hover:bg-white/[0.06] hover:text-white"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="max-h-56 overflow-y-auto p-3 font-mono text-xs divide-y divide-white/[0.03]">
        {logs.length === 0 ? (
          <div className="py-6 text-center text-slate-500">
            No events logged yet.
          </div>
        ) : (
          logs.map((log) => {
            const levelColor =
              log.level === 'action'
                ? 'text-amber-400 bg-amber-400/10 border-amber-400/20'
                : log.level === 'system'
                ? 'text-indigo-400 bg-indigo-400/10 border-indigo-400/20'
                : 'text-cyan-400 bg-cyan-400/10 border-cyan-400/20'

            return (
              <div key={log.id} className="py-2 flex items-start gap-3">
                <span className="text-[10px] text-slate-500 shrink-0 select-none">
                  {log.timestamp}
                </span>
                <span
                  className={`rounded border px-1.5 py-0.2 text-[9px] uppercase tracking-wider font-semibold shrink-0 ${levelColor}`}
                >
                  {log.level}
                </span>
                <div className="flex flex-col flex-1 min-w-0">
                  <span className="text-slate-200 break-words">{log.message}</span>
                  {log.detail && (
                    <span className="mt-0.5 text-[11px] text-slate-400 break-words">
                      {log.detail}
                    </span>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
