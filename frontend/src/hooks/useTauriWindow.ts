import { useCallback, useEffect, useState } from 'react'
import { invoke, isTauri } from '@tauri-apps/api/core'

export type HudWindowMode = 'pill' | 'expanded'

export function useTauriWindow() {
  const [isNativeApp, setIsNativeApp] = useState(false)
  const [hudMode, setHudModeState] = useState<HudWindowMode>('expanded')

  useEffect(() => {
    setIsNativeApp(isTauri())
  }, [])

  const setHudMode = useCallback(async (mode: HudWindowMode) => {
    setHudModeState(mode)
    if (isTauri()) {
      try {
        await invoke('set_hud_mode', { mode })
      } catch (err) {
        console.warn('Failed to set HUD mode in Tauri:', err)
      }
    }
  }, [])

  const setClickThrough = useCallback(async (ignore: boolean) => {
    if (isTauri()) {
      try {
        await invoke('set_click_through', { ignore })
      } catch (err) {
        console.warn('Failed to set click-through in Tauri:', err)
      }
    }
  }, [])

  return {
    isNativeApp,
    hudMode,
    setHudMode,
    setClickThrough,
  }
}
