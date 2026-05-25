import { create } from 'zustand'

export type SophiaMode = 'ai' | 'human_takeover'

export interface TurnSignals {
  confidence_score: number
  trust_score: number
  deal_heat: number
  handoff_recommended: boolean
  signal_notes: string[]
}

export interface ContextPacket {
  seller_name: string | null
  address: string | null
  phone: string | null
  motivation: string | null
  timeline: string | null
  emotional_state: string | null
  deal_heat: number
  trust_score: number
  confidence_score: number
  transfer_reason: string
  objections_raised: string[]
  key_moments: string[]
  sophia_summary: string
  turn_count: number
  tokens_used: number
  built_at: string
}

interface SophiaState {
  sessionId: string | null
  mode: SophiaMode
  signals: TurnSignals | null
  contextPacket: ContextPacket | null
  isTransferring: boolean
  transferError: string | null
  setSessionId: (id: string | null) => void
  setMode: (mode: SophiaMode) => void
  setSignals: (signals: TurnSignals) => void
  setContextPacket: (packet: ContextPacket) => void
  setTransferring: (val: boolean) => void
  setTransferError: (err: string | null) => void
  reset: () => void
}

const initialState = {
  sessionId: null,
  mode: 'ai' as SophiaMode,
  signals: null,
  contextPacket: null,
  isTransferring: false,
  transferError: null,
}

export const useSophiaStore = create<SophiaState>((set) => ({
  ...initialState,
  setSessionId: (sessionId) => set({ sessionId }),
  setMode: (mode) => set({ mode }),
  setSignals: (signals) => set({ signals }),
  setContextPacket: (contextPacket) => set({ contextPacket }),
  setTransferring: (isTransferring) => set({ isTransferring }),
  setTransferError: (transferError) => set({ transferError }),
  reset: () => set(initialState),
}))