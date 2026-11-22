import { useCallback, useEffect, useState } from 'react'
import { invoke, isTauri } from '@tauri-apps/api/core'

export type HudWindowMode = 'pill' | 'expanded'

export interface BackendProcessStatus {
  is_online: boolean
  is_managed: boolean
  message: string
}

export function useTauriWindow() {
  const [isNativeApp, setIsNativeApp] = useState(false)
  const [hudMode, setHudModeState] = useState<HudWindowMode>('expanded')
  const [backendStatus, setBackendStatus] = useState<BackendProcessStatus | null>(null)

  useEffect(() => {
    setIsNativeApp(isTauri())
  }, [])

  const fetchBackendStatus = useCallback(async () => {
    if (isTauri()) {
      try {
        const res = await invoke<BackendProcessStatus>('get_backend_status')
        setBackendStatus(res)
        return res
      } catch (err) {
        console.warn('Failed to query backend status in Tauri:', err)
      }
    }
    return null
  }, [])

  const startBackend = useCallback(async () => {
    if (isTauri()) {
      try {
        const res = await invoke<BackendProcessStatus>('start_backend')
        setBackendStatus(res)
        return res
      } catch (err) {
        console.warn('Failed to start backend in Tauri:', err)
      }
    }
    return null
  }, [])

  const stopBackend = useCallback(async () => {
    if (isTauri()) {
      try {
        await invoke('stop_backend')
        setBackendStatus({
          is_online: false,
          is_managed: false,
          message: 'Backend stopped by user.',
        })
      } catch (err) {
        console.warn('Failed to stop backend in Tauri:', err)
      }
    }
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
    backendStatus,
    fetchBackendStatus,
    startBackend,
    stopBackend,
    setHudMode,
    setClickThrough,
  }
}
