import { Activity, Battery, BatteryCharging, Cpu, HardDrive, Wifi } from 'lucide-react'
import type { TelemetryData } from '../types/hud'

interface TelemetryStripProps {
  telemetry: TelemetryData
  onToggleDrawer: () => void
  isDrawerOpen: boolean
  logCount: number
}

export function TelemetryStrip({
  telemetry,
  onToggleDrawer,
  isDrawerOpen,
  logCount,
}: TelemetryStripProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-white/[0.06] bg-slate-900/60 px-4 py-2 text-xs shadow-[inset_0_1px_0_0_rgba(255,255,255,0.04)] backdrop-blur-md">
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-1.5 text-slate-400">
          <Cpu className="h-3.5 w-3.5 text-slate-400" />
          <span className="font-medium uppercase tracking-wider text-[10px] text-slate-400">CPU</span>
          <span className="font-mono text-slate-200 tabular-nums">{telemetry.cpuUsage}%</span>
        </div>

        <div className="flex items-center gap-1.5 text-slate-400">
          <HardDrive className="h-3.5 w-3.5 text-slate-400" />
          <span className="font-medium uppercase tracking-wider text-[10px] text-slate-400">RAM</span>
          <span className="font-mono text-slate-200 tabular-nums">
            {telemetry.memoryUsed.toFixed(1)} / {telemetry.memoryTotal} GB
          </span>
        </div>

        {telemetry.battery && (
          <div className="flex items-center gap-1.5 text-slate-400">
            {telemetry.battery.power_plugged ? (
              <BatteryCharging className="h-3.5 w-3.5 text-emerald-400" />
            ) : (
              <Battery className="h-3.5 w-3.5 text-slate-400" />
            )}
            <span className="font-medium uppercase tracking-wider text-[10px] text-slate-400">PWR</span>
            <span className="font-mono text-slate-200 tabular-nums">
              {telemetry.battery.percent}%
            </span>
          </div>
        )}

        <div className="flex items-center gap-1.5 text-slate-400">
          <Wifi className={`h-3.5 w-3.5 ${telemetry.isConnected ? 'text-emerald-400' : 'text-rose-400'}`} />
          <span className="font-medium uppercase tracking-wider text-[10px] text-slate-400">LINK</span>
          <span className="font-mono text-slate-200 tabular-nums">{telemetry.pingMs}ms</span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          type="button"
          onClick={onToggleDrawer}
          className={`flex items-center gap-1.5 rounded-lg border px-2.5 py-1 font-mono text-[11px] transition-all duration-150 active:scale-95 ${
            isDrawerOpen
              ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-300'
              : 'border-white/[0.08] bg-slate-950/40 text-slate-300 hover:border-white/20 hover:text-white'
          }`}
        >
          <Activity className="h-3 w-3" />
          <span>Events</span>
          <span className="rounded bg-white/[0.08] px-1 py-0.2 text-[9px] text-slate-300">
            {logCount}
          </span>
        </button>
      </div>
    </div>
  )
}
