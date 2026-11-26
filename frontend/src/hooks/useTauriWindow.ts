import { useCallback, useState, type MouseEvent } from 'react'
import { invoke, isTauri } from '@tauri-apps/api/core'
import { getCurrentWindow } from '@tauri-apps/api/window'

export type HudWindowMode = 'pill' | 'expanded'

export async function startWindowDrag(e: MouseEvent) {
  if (!isTauri()) return
  if ((e.target as HTMLElement).closest('button, input, textarea, a')) return

  try {
    await invoke('drag_window')
  } catch {
    try {
      await getCurrentWindow().startDragging()
    } catch {
      // Ignore outside native window context
    }
  }
}

export function useTauriWindow() {
  const [hudMode, setHudModeState] = useState<HudWindowMode>('expanded')

  const setHudMode = useCallback(async (mode: HudWindowMode) => {
    setHudModeState(mode)
    if (isTauri()) {
      try {
        await invoke('set_hud_mode', { mode })
      } catch {
        // Ignore if window handle is unavailable during teardown
      }
    }
  }, [])

  return {
    hudMode,
    setHudMode,
  }
}
