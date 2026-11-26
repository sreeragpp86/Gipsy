import { useState, useEffect, useRef, useCallback } from 'react'
import { invoke, isTauri } from '@tauri-apps/api/core'
import type { AdminAuthChallenge, AssistantState, DialogueItem, LogEntry, TelemetryData } from '../types/hud'

export function useGipsySocket(url: string = 'ws://127.0.0.1:8000/ws') {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected')
  const [assistantState, setAssistantState] = useState<AssistantState>('IDLE')
  const [isMicActive, setIsMicActive] = useState<boolean>(true)
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false)
  const [audioAmplitude, setAudioAmplitude] = useState<number>(0)
  const [adminChallenge, setAdminChallenge] = useState<AdminAuthChallenge | null>(null)

  const [telemetry, setTelemetry] = useState<TelemetryData>({
    cpuUsage: 0,
    memoryUsed: 0,
    memoryTotal: 16,
    pingMs: 0,
    isConnected: false,
    battery: null,
  })

  const [dialogue, setDialogue] = useState<DialogueItem[]>([
    {
      id: 'init-0',
      sender: 'assistant',
      text: 'Gipsy HUD connected. Listening for voice input or terminal instructions.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ])

  const [logs, setLogs] = useState<LogEntry[]>([])

  const socketRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pingTimestampRef = useRef<number>(0)
  const isUnmountedRef = useRef<boolean>(false)

  const addLog = useCallback((level: LogEntry['level'], message: string, detail?: string) => {
    const entry: LogEntry = {
      id: `log-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      level,
      message,
      detail,
    }
    setLogs((prev) => [entry, ...prev.slice(0, 49)])
  }, [])

  const connect = useCallback(async () => {
    if (isUnmountedRef.current) return

    setStatus('connecting')

    let finalUrl = url
    if (isTauri()) {
      try {
        const token = await invoke<string>('get_auth_token')
        if (token) {
          const sep = finalUrl.includes('?') ? '&' : '?'
          finalUrl = `${finalUrl}${sep}token=${encodeURIComponent(token)}`
        }
      } catch {
        // Fallback for non-Tauri dev mode
      }
    }

    try {
      const ws = new WebSocket(finalUrl)
      socketRef.current = ws

      ws.onopen = () => {
        if (isUnmountedRef.current) {
          ws.close()
          return
        }
        setStatus('connected')
        setTelemetry((prev) => ({ ...prev, isConnected: true, pingMs: 1 }))
        addLog('system', 'WebSocket connection established', finalUrl)
        pingTimestampRef.current = Date.now()
        ws.send(JSON.stringify({ type: 'ping' }))
      }

      ws.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          const msgType = payload.type

          if (msgType === 'connection_ack') {
            if (payload.telemetry) {
              setTelemetry((prev) => ({
                ...prev,
                cpuUsage: payload.telemetry.cpu_usage,
                memoryUsed: payload.telemetry.memory_used,
                memoryTotal: payload.telemetry.memory_total,
                battery: payload.telemetry.battery,
              }))
            }
            if (payload.state) {
              setAssistantState(payload.state)
            }
          } else if (msgType === 'telemetry') {
            const data = payload.data
            setTelemetry((prev) => ({
              ...prev,
              cpuUsage: data.cpu_usage,
              memoryUsed: data.memory_used,
              memoryTotal: data.memory_total,
              battery: data.battery,
            }))
          } else if (msgType === 'state_change') {
            setAssistantState(payload.state)
            if (payload.state === 'IDLE') {
              setAudioAmplitude(0)
            } else if (payload.state === 'LISTENING') {
              setIsMicActive(true)
            }
          } else if (msgType === 'audio_amplitude') {
            setAudioAmplitude(payload.amplitude ?? 0)
          } else if (msgType === 'user_speech') {
            const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            setDialogue((prev) => [
              ...prev,
              {
                id: `speech-${Date.now()}`,
                sender: 'user',
                text: payload.text,
                timestamp: timeString,
              },
            ])
          } else if (msgType === 'tool_call') {
            setDialogue((prev) => {
              const last = prev[prev.length - 1]
              if (last && last.sender === 'assistant' && last.tool) {
                return [
                  ...prev.slice(0, -1),
                  {
                    ...last,
                    tool: {
                      name: payload.name,
                      status: payload.status,
                    },
                  },
                ]
              }
              return prev
            })
          } else if (msgType === 'stream_chunk') {
            setDialogue((prev) => {
              const last = prev[prev.length - 1]
              if (last && last.sender === 'assistant' && last.isStreaming) {
                return [
                  ...prev.slice(0, -1),
                  {
                    ...last,
                    text: last.text + payload.chunk,
                  },
                ]
              }
              return [
                ...prev,
                {
                  id: `stream-${Date.now()}`,
                  sender: 'assistant',
                  text: payload.chunk,
                  timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
                  isStreaming: true,
                },
              ]
            })
          } else if (msgType === 'assistant_message') {
            const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            setDialogue((prev) => {
              const last = prev[prev.length - 1]
              if (last && last.sender === 'assistant' && last.isStreaming) {
                return [
                  ...prev.slice(0, -1),
                  {
                    ...last,
                    text: payload.content || last.text,
                    isStreaming: false,
                    tool: payload.tool || last.tool,
                  },
                ]
              }
              return [
                ...prev,
                {
                  id: `msg-${Date.now()}`,
                  sender: 'assistant',
                  text: payload.content,
                  timestamp: timeString,
                  tool: payload.tool,
                },
              ]
            })
          } else if (msgType === 'log') {
            addLog(payload.level || 'info', payload.message, payload.detail)
          } else if (msgType === 'admin_auth_required') {
            setAdminChallenge({
              challenge_id: payload.challenge_id,
              tool_name: payload.tool_name,
              arguments: payload.arguments || {},
              prompt: payload.prompt,
              expires_in: payload.expires_in || 30,
            })
            addLog('system', 'Admin Authorization Required', `${payload.tool_name}`)
          } else if (msgType === 'admin_auth_result') {
            setAdminChallenge(null)
            addLog(payload.success ? 'action' : 'system', payload.message || 'Authorization result')
          } else if (msgType === 'pong') {
            const delta = Math.max(1, Date.now() - pingTimestampRef.current)
            setTelemetry((prev) => ({ ...prev, pingMs: delta, isConnected: true }))
          }
        } catch {
        }
      }

      ws.onclose = () => {
        setStatus('disconnected')
        setTelemetry((prev) => ({ ...prev, isConnected: false, pingMs: 0 }))
        addLog('system', 'WebSocket connection closed. Retrying...')
        scheduleReconnect()
      }

      ws.onerror = () => {
        ws.close()
      }
    } catch {
      scheduleReconnect()
    }
  }, [url, addLog])

  const scheduleReconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    reconnectTimeoutRef.current = setTimeout(() => {
      connect()
    }, 2000)
  }, [connect])

  useEffect(() => {
    isUnmountedRef.current = false
    connect()

    const pingInterval = setInterval(() => {
      if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
        pingTimestampRef.current = Date.now()
        socketRef.current.send(JSON.stringify({ type: 'ping' }))
      }
    }, 3000)

    return () => {
      isUnmountedRef.current = true
      clearInterval(pingInterval)
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (socketRef.current) {
        socketRef.current.close()
      }
    }
  }, [connect])

  const sendCommand = useCallback((content: string) => {
    const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    setDialogue((prev) => [
      ...prev,
      {
        id: `user-${Date.now()}`,
        sender: 'user',
        text: content,
        timestamp: timeString,
      },
    ])

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: 'text_command',
          content,
        })
      )
    } else {
      addLog('system', 'Cannot send command: WebSocket offline')
    }
  }, [addLog])

  const toggleMic = useCallback(() => {
    const nextState = !isMicActive
    setIsMicActive(nextState)

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: 'toggle_mic',
          active: nextState,
        })
      )
    }
  }, [isMicActive])

  const clearLogs = useCallback(() => {
    setLogs([])
  }, [])

  const submitAdminAuth = useCallback((challenge_id: string, password: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: 'admin_auth_submit',
          challenge_id,
          password,
        })
      )
    }
  }, [])

  const cancelAdminAuth = useCallback((challenge_id: string) => {
    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: 'admin_auth_cancel',
          challenge_id,
        })
      )
    }
    setAdminChallenge(null)
  }, [])

  return {
    status,
    assistantState,
    isMicActive,
    isDrawerOpen,
    setIsDrawerOpen,
    audioAmplitude,
    adminChallenge,
    telemetry,
    dialogue,
    logs,
    sendCommand,
    toggleMic,
    clearLogs,
    submitAdminAuth,
    cancelAdminAuth,
  }
}
