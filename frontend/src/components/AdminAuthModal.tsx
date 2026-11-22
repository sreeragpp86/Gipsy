import { useState, useEffect, useRef, type FormEvent } from 'react'
import { ShieldAlert, KeyRound, X, AlertTriangle } from 'lucide-react'
import type { AdminAuthChallenge } from '../types/hud'

interface AdminAuthModalProps {
  challenge: AdminAuthChallenge
  onSubmit: (challengeId: string, password: string) => void
  onCancel: (challengeId: string) => void
}

export function AdminAuthModal({ challenge, onSubmit, onCancel }: AdminAuthModalProps) {
  const [password, setPassword] = useState('')
  const [timeLeft, setTimeLeft] = useState(challenge.expires_in || 30)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    const timer = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timer)
          onCancel(challenge.challenge_id)
          return 0
        }
        return prev - 1
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [challenge.challenge_id, onCancel])

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onCancel(challenge.challenge_id)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [challenge.challenge_id, onCancel])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (!password.trim()) return
    onSubmit(challenge.challenge_id, password)
  }

  const targetDescription = () => {
    if (challenge.tool_name === 'open_application') {
      return String(challenge.arguments.app_name || 'System Application')
    }
    if (challenge.tool_name === 'run_quick_action') {
      const act = String(challenge.arguments.action || '')
      const tgt = String(challenge.arguments.target || '')
      return tgt ? `${act} -> ${tgt}` : act
    }
    return challenge.tool_name
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-md">
      <div className="relative w-full max-w-md overflow-hidden rounded-2xl border border-amber-500/30 bg-slate-900/95 p-6 shadow-[0_0_50px_-10px_rgba(245,158,11,0.25)]">
        <button
          type="button"
          onClick={() => onCancel(challenge.challenge_id)}
          className="absolute right-4 top-4 text-slate-400 hover:text-slate-200 transition-colors"
        >
          <X size={18} />
        </button>

        <div className="flex items-center gap-3 mb-4">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-amber-500/15 border border-amber-500/30 text-amber-400 shadow-[0_0_15px_rgba(245,158,11,0.2)]">
            <ShieldAlert size={22} />
          </div>
          <div>
            <h2 className="text-sm font-semibold tracking-wide text-white">Elevated Security Gate</h2>
            <p className="text-xs text-amber-300/80 font-mono">Tier 2 Admin Authorization</p>
          </div>
        </div>

        <div className="mb-5 rounded-xl border border-white/[0.06] bg-slate-950/60 p-3.5 space-y-2 text-xs">
          <div className="flex items-center justify-between text-slate-400">
            <span>Target Tool:</span>
            <span className="font-mono text-cyan-300 font-medium">{challenge.tool_name}</span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span>Action / Target:</span>
            <span className="font-mono text-slate-200 font-medium">{targetDescription()}</span>
          </div>
          <div className="flex items-center justify-between text-slate-400">
            <span>Time Remaining:</span>
            <span className={`font-mono font-medium ${timeLeft <= 5 ? 'text-rose-400 animate-pulse' : 'text-amber-300'}`}>
              {timeLeft}s
            </span>
          </div>
          <div className="pt-1 flex items-start gap-1.5 text-[11px] text-slate-400 border-t border-white/[0.04]">
            <AlertTriangle size={13} className="shrink-0 text-amber-400 mt-0.5" />
            <span>High-privilege system command requested. Confirm by entering macOS administrator credentials.</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3 text-slate-400">
              <KeyRound size={15} />
            </div>
            <input
              ref={inputRef}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter administrator password..."
              className="w-full rounded-xl border border-white/10 bg-slate-950/80 pl-9 pr-4 py-2.5 text-xs text-slate-100 placeholder-slate-500 focus:border-amber-500/50 focus:outline-none focus:ring-1 focus:ring-amber-500/50"
            />
          </div>

          <div className="flex items-center justify-end gap-2.5 pt-1">
            <button
              type="button"
              onClick={() => onCancel(challenge.challenge_id)}
              className="rounded-xl border border-white/[0.08] bg-slate-800/60 px-4 py-2 text-xs font-medium text-slate-300 hover:bg-slate-800 transition-colors"
            >
              Deny & Cancel
            </button>
            <button
              type="submit"
              disabled={!password.trim()}
              className="rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 px-4 py-2 text-xs font-semibold text-slate-950 shadow-md shadow-amber-500/20 hover:from-amber-400 hover:to-amber-500 disabled:opacity-40 disabled:cursor-not-allowed transition-all"
            >
              Authorize Operation
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
