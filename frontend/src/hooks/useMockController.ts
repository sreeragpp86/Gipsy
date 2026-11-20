import { useState, useEffect, useCallback, useRef } from 'react'
import type { AssistantState, DialogueItem, LogEntry, TelemetryData } from '../types/hud'

export function useMockController() {
  const [state, setState] = useState<AssistantState>('IDLE')
  const [isMicActive, setIsMicActive] = useState<boolean>(false)
  const [isDrawerOpen, setIsDrawerOpen] = useState<boolean>(false)

  const [telemetry, setTelemetry] = useState<TelemetryData>({
    cpuUsage: 14,
    memoryUsed: 4.2,
    memoryTotal: 16.0,
    pingMs: 18,
    isConnected: true,
  })

  const [dialogue, setDialogue] = useState<DialogueItem[]>([
    {
      id: 'init-1',
      sender: 'assistant',
      text: 'Gipsy HUD ready. Listening for voice commands or terminal instructions.',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ])

  const [logs, setLogs] = useState<LogEntry[]>([
    {
      id: 'log-1',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      level: 'system',
      message: 'Kernel initialized',
      detail: 'Audio pipeline: CoreAudio • Speech model: Whisper-v3-Turbo',
    },
    {
      id: 'log-2',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      level: 'info',
      message: 'WebSocket stream established',
      detail: 'Local loopback: 127.0.0.1:8000/ws',
    },
  ])

  const activeTimersRef = useRef<ReturnType<typeof setTimeout>[]>([])

  const clearTimers = () => {
    activeTimersRef.current.forEach(clearTimeout)
    activeTimersRef.current = []
  }

  const addLog = useCallback((level: LogEntry['level'], message: string, detail?: string) => {
    const newEntry: LogEntry = {
      id: `log-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
      level,
      message,
      detail,
    }
    setLogs((prev) => [newEntry, ...prev.slice(0, 49)])
  }, [])

  useEffect(() => {
    const interval = setInterval(() => {
      setTelemetry((prev) => ({
        ...prev,
        cpuUsage: Math.floor(12 + Math.random() * 16),
        memoryUsed: Number((4.1 + Math.random() * 0.4).toFixed(1)),
        pingMs: Math.floor(14 + Math.random() * 8),
      }))
    }, 2500)

    return () => clearInterval(interval)
  }, [])

  const executePipeline = useCallback((commandText: string) => {
    clearTimers()

    const timeString = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    const userMsgId = `msg-${Date.now()}`

    setDialogue((prev) => [
      ...prev,
      {
        id: userMsgId,
        sender: 'user',
        text: commandText,
        timestamp: timeString,
      },
    ])

    setState('PROCESSING')
    addLog('info', `Received command: "${commandText}"`)

    const isOSCommand =
      /open|launch|volume|brightness|screen|app|finder|terminal|mute|window/i.test(commandText)

    const timer1 = setTimeout(() => {
      const assistantMsgId = `msg-${Date.now() + 1}`

      if (isOSCommand) {
        setState('EXECUTING_TOOL')
        const toolName = `os.dispatch_action("${commandText}")`
        addLog('action', 'Executing OS controller action', toolName)

        setDialogue((prev) => [
          ...prev,
          {
            id: assistantMsgId,
            sender: 'assistant',
            text: `Executing system action for: ${commandText}`,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            tool: {
              name: toolName,
              status: 'running',
            },
          },
        ])

        const timer2 = setTimeout(() => {
          setDialogue((prev) =>
            prev.map((item) =>
              item.id === assistantMsgId
                ? {
                    ...item,
                    text: `Successfully executed system instruction: "${commandText}".`,
                    tool: item.tool ? { ...item.tool, status: 'completed' } : undefined,
                  }
                : item
            )
          )
          setState('SPEAKING')
          addLog('info', 'Command output returned to voice synthesizer')

          const timer3 = setTimeout(() => {
            setState('IDLE')
            addLog('system', 'State returned to IDLE')
          }, 2000)
          activeTimersRef.current.push(timer3)
        }, 1200)

        activeTimersRef.current.push(timer2)
      } else {
        setState('SPEAKING')
        const replyText = `Processed: "${commandText}". Standing by for OS directives.`
        addLog('info', 'Streaming response', replyText)

        setDialogue((prev) => [
          ...prev,
          {
            id: assistantMsgId,
            sender: 'assistant',
            text: replyText,
            timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          },
        ])

        const timer2 = setTimeout(() => {
          setState('IDLE')
          addLog('system', 'State returned to IDLE')
        }, 1800)
        activeTimersRef.current.push(timer2)
      }
    }, 700)

    activeTimersRef.current.push(timer1)
  }, [addLog])

  const toggleMic = useCallback(() => {
    if (isMicActive) {
      setIsMicActive(false)
      clearTimers()
      setState('PROCESSING')
      addLog('info', 'Microphone closed, synthesizing input')

      const timer = setTimeout(() => {
        executePipeline('Toggle terminal fullscreen and set volume to 75%')
      }, 500)
      activeTimersRef.current.push(timer)
    } else {
      clearTimers()
      setIsMicActive(true)
      setState('LISTENING')
      addLog('action', 'Microphone opened, stream active')
    }
  }, [isMicActive, addLog, executePipeline])

  const selectState = useCallback((targetState: AssistantState) => {
    clearTimers()
    setIsMicActive(targetState === 'LISTENING')
    setState(targetState)
    addLog('system', `Manual state override: ${targetState}`)
  }, [addLog])

  const clearLogs = useCallback(() => {
    setLogs([])
  }, [])

  return {
    state,
    isMicActive,
    telemetry,
    dialogue,
    logs,
    isDrawerOpen,
    setIsDrawerOpen,
    toggleMic,
    executePipeline,
    selectState,
    clearLogs,
  }
}
