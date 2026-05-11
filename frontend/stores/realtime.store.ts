import { create } from 'zustand'

interface RealtimeState {
  subscribedChannels: Set<string>
  lastEventAt: number | null
  eventCount: number

  addChannel: (channel: string) => void
  removeChannel: (channel: string) => void
  recordEvent: () => void
  reset: () => void
}

export const useRealtimeStore = create<RealtimeState>()((set) => ({
  subscribedChannels: new Set(),
  lastEventAt: null,
  eventCount: 0,

  addChannel: (channel) =>
    set((s) => ({ subscribedChannels: new Set([...s.subscribedChannels, channel]) })),
  removeChannel: (channel) =>
    set((s) => {
      const next = new Set(s.subscribedChannels)
      next.delete(channel)
      return { subscribedChannels: next }
    }),
  recordEvent: () =>
    set((s) => ({ lastEventAt: Date.now(), eventCount: s.eventCount + 1 })),
  reset: () => set({ subscribedChannels: new Set(), lastEventAt: null, eventCount: 0 }),
}))
