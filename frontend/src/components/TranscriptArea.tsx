import { Terminal, CheckCircle2, Loader2, User } from 'lucide-react'
import type { DialogueItem } from '../types/hud'

interface TranscriptAreaProps {
  dialogue: DialogueItem[]
}

export function TranscriptArea({ dialogue }: TranscriptAreaProps) {
  if (dialogue.length === 0) {
    return (
      <div className="flex h-36 w-full flex-col items-center justify-center rounded-2xl border border-white/[0.04] bg-slate-900/30 p-6 text-center text-slate-500">
        <p className="text-sm font-normal text-slate-400">Ready for voice input or commands</p>
        <p className="mt-1 font-mono text-xs text-slate-600">Press the microphone or type below</p>
      </div>
    )
  }

  const latestItems = dialogue.slice(-3)

  return (
    <div className="flex w-full flex-col gap-3 rounded-2xl border border-white/[0.06] bg-slate-900/40 p-4 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.03)] backdrop-blur-md">
      {latestItems.map((item) => {
        const isUser = item.sender === 'user'

        return (
          <div
            key={item.id}
            className={`flex flex-col gap-1.5 rounded-xl p-3.5 transition-all duration-200 ${
              isUser
                ? 'border border-white/[0.04] bg-slate-950/40'
                : 'border border-cyan-500/10 bg-slate-900/60'
            }`}
          >
            <div className="flex items-center justify-between text-[11px]">
              <div className="flex items-center gap-1.5 font-medium">
                {isUser ? (
                  <>
                    <User className="h-3 w-3 text-slate-400" />
                    <span className="text-slate-300">You</span>
                  </>
                ) : (
                  <>
                    <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                    <span className="text-cyan-200 font-semibold">Gipsy</span>
                  </>
                )}
              </div>
              <span className="font-mono text-[10px] text-slate-500">{item.timestamp}</span>
            </div>

            <p className="text-sm leading-relaxed text-slate-200">
              {item.text}
              {item.isStreaming && (
                <span className="ml-1 inline-block h-3 w-1 animate-pulse bg-cyan-400 align-middle" />
              )}
            </p>

            {item.tool && (
              <div className="mt-1 flex items-center gap-2 rounded-lg border border-amber-500/20 bg-amber-500/[0.04] px-2.5 py-1 text-xs">
                <Terminal className="h-3.5 w-3.5 text-amber-400" />
                <span className="font-mono text-[11px] text-amber-200/90">{item.tool.name}</span>
                <span className="ml-auto flex items-center gap-1 font-mono text-[10px] text-amber-300/70">
                  {item.tool.status === 'running' ? (
                    <>
                      <Loader2 className="h-3 w-3 animate-spin text-amber-400" />
                      <span>Running</span>
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="h-3 w-3 text-emerald-400" />
                      <span>Completed</span>
                    </>
                  )}
                </span>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
