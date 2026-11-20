export type AssistantState = 'IDLE' | 'LISTENING' | 'PROCESSING' | 'EXECUTING_TOOL' | 'SPEAKING'

export interface BatteryData {
  percent: number
  power_plugged: boolean
}

export interface TelemetryData {
  cpuUsage: number
  memoryUsed: number
  memoryTotal: number
  pingMs: number
  isConnected: boolean
  battery?: BatteryData | null
}

export interface LogEntry {
  id: string
  timestamp: string
  level: 'info' | 'action' | 'system'
  message: string
  detail?: string
}

export interface DialogueItem {
  id: string
  sender: 'user' | 'assistant'
  text: string
  timestamp: string
  isStreaming?: boolean
  tool?: {
    name: string
    status: 'running' | 'completed'
  }
}
