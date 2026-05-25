import { create } from 'zustand'

interface RealtimeState {
  /** Server-confirmed subscriptions. Cleared on reconnect. */
  subscribedChannels: Set<string>
  /** Channels the client intends to be subscribed to. Survives reconnect. */
  intendedChannels: Set<string>
  /** Last received event_id per channel. Used as replay cursor on reconnect. */
  lastEventIds: Record<string, string>
  lastEventAt: number | null
  eventCount: number

  addChannel: (channel: string) => void
  removeChannel: (channel: string) => void
  intendChannel: (channel: string) => void
  unintendChannel: (channel: string) => void
  setLastEventId: (channel: string, eventId: string) => void
  recordEvent: () => void
  /** Reset transient state only — keeps intendedChannels and lastEventIds. */
  reset: () => void
}

export const useRealtimeStore = create<RealtimeState>()((set) => ({
  subscribedChannels: new Set(),
  intendedChannels: new Set(),
  lastEventIds: {},
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

  intendChannel: (channel) =>
    set((s) => ({ intendedChannels: new Set([...s.intendedChannels, channel]) })),

  unintendChannel: (channel) =>
    set((s) => {
      const next = new Set(s.intendedChannels)
      next.delete(channel)
      return { intendedChannels: next }
    }),

  setLastEventId: (channel, eventId) =>
    set((s) => ({ lastEventIds: { ...s.lastEventIds, [channel]: eventId } })),

  recordEvent: () =>
    set((s) => ({ lastEventAt: Date.now(), eventCount: s.eventCount + 1 })),

  /** Clears confirmed subscriptions and counters. intendedChannels and lastEventIds survive. */
  reset: () => set({ subscribedChannels: new Set(), lastEventAt: null, eventCount: 0 }),
}))
