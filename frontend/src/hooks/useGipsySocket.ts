import { useState, useEffect, useRef, useCallback } from 'react'
import type { AssistantState, DialogueItem, LogEntry, TelemetryData } from '../types/hud'

export function useGipsySocket(url: string = 'ws://localhost:8000/ws') {
  const [status, setStatus] = useState<'connecting' | 'connected' | 'disconnected'>('disconnected')
  const [assistantState, setAssistantState] = useState<AssistantState>('IDLE')
  const [isMicActive, setIsMicActive] = useState<boolean>(false)
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false)

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

  const connect = useCallback(() => {
    if (isUnmountedRef.current) return

    setStatus('connecting')

    try {
      const ws = new WebSocket(url)
      socketRef.current = ws

      ws.onopen = () => {
        if (isUnmountedRef.current) {
          ws.close()
          return
        }
        setStatus('connected')
        setTelemetry((prev) => ({ ...prev, isConnected: true }))
        addLog('system', 'WebSocket connection established', url)
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
              setIsMicActive(false)
            }
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
          } else if (msgType === 'assistant_message') {
            const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
            setDialogue((prev) => [
              ...prev,
              {
                id: `msg-${Date.now()}`,
                sender: 'assistant',
                text: payload.content,
                timestamp: timeString,
                tool: payload.tool,
              },
            ])
          } else if (msgType === 'log') {
            addLog(payload.level || 'info', payload.message, payload.detail)
          } else if (msgType === 'pong') {
            const delta = Date.now() - pingTimestampRef.current
            setTelemetry((prev) => ({ ...prev, pingMs: delta }))
          }
        } catch {
        }
      }

      ws.onclose = () => {
        setStatus('disconnected')
        setTelemetry((prev) => ({ ...prev, isConnected: false }))
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

  const setOverrideState = useCallback((state: AssistantState) => {
    setAssistantState(state)
    setIsMicActive(state === 'LISTENING')

    if (socketRef.current && socketRef.current.readyState === WebSocket.OPEN) {
      socketRef.current.send(
        JSON.stringify({
          type: 'set_state',
          state,
        })
      )
    }
  }, [])

  const toggleMic = useCallback(() => {
    if (isMicActive) {
      setIsMicActive(false)
      sendCommand('Toggle terminal fullscreen and set volume to 75%')
    } else {
      setIsMicActive(true)
      setOverrideState('LISTENING')
      addLog('action', 'Microphone active, listening for speech stream')
    }
  }, [isMicActive, sendCommand, setOverrideState, addLog])

  const clearLogs = useCallback(() => {
    setLogs([])
  }, [])

  return {
    status,
    assistantState,
    isMicActive,
    isDrawerOpen,
    setIsDrawerOpen,
    telemetry,
    dialogue,
    logs,
    sendCommand,
    setOverrideState,
    toggleMic,
    clearLogs,
  }
}
