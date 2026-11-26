import { useEffect } from 'react'
import { Check, ShieldAlert, X } from 'lucide-react'
import type { ConfirmRequest } from '../types/hud'

interface ConfirmActionCardProps {
  request: ConfirmRequest
  onRespond: (requestId: string, approved: boolean) => void
}

export function ConfirmActionCard({ request, onRespond }: ConfirmActionCardProps) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        e.preventDefault()
        e.stopPropagation()
        onRespond(request.request_id, true)
      } else if (e.key === 'Escape') {
        e.preventDefault()
        e.stopPropagation()
        onRespond(request.request_id, false)
      }
    }
    window.addEventListener('keydown', handleKeyDown, true)
    return () => window.removeEventListener('keydown', handleKeyDown, true)
  }, [request.request_id, onRespond])

  return (
    <div className="rounded-xl border border-rose-500/40 bg-slate-950/90 p-3.5 shadow-[0_0_24px_-4px_rgba(244,63,94,0.3)] backdrop-blur-xl">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-rose-500/35 bg-rose-500/15 text-rose-400">
            <ShieldAlert size={16} />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold tracking-wide text-white">
                Confirm Risky Action
              </span>
              <span className="rounded border border-rose-500/30 bg-rose-500/10 px-1.5 py-0.5 font-mono text-[10px] text-rose-300">
                {request.tool}
              </span>
            </div>
            <pre className="mt-1.5 max-h-20 overflow-auto rounded-lg border border-white/[0.06] bg-black/40 px-2.5 py-1.5 font-mono text-[11px] text-slate-200">
              {JSON.stringify(request.args, null, 2)}
            </pre>
          </div>
        </div>
      </div>

      <div className="mt-3 flex items-center justify-end gap-2">
        <button
          type="button"
          onClick={() => onRespond(request.request_id, false)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-white/10 bg-slate-800/80 px-3 py-1.5 text-xs font-medium text-slate-200 transition-colors hover:bg-slate-700"
        >
          <X size={13} />
          <span>Deny</span>
          <kbd className="ml-1 rounded bg-black/40 px-1 font-mono text-[10px] text-slate-400">
            Esc
          </kbd>
        </button>
        <button
          type="button"
          onClick={() => onRespond(request.request_id, true)}
          className="inline-flex items-center gap-1.5 rounded-lg bg-rose-500 px-3 py-1.5 text-xs font-semibold text-white shadow-md shadow-rose-500/20 transition-colors hover:bg-rose-400"
        >
          <Check size={13} />
          <span>Approve</span>
          <kbd className="ml-1 rounded bg-rose-700/60 px-1 font-mono text-[10px] text-rose-100">
            ↵
          </kbd>
        </button>
      </div>
    </div>
  )
}
