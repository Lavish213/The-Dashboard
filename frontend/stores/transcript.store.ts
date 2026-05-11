import { create } from 'zustand'

/**
 * Transcript store — Phase 2 shell.
 * Streaming, playback, and indexing implemented in Phase 6.
 */

interface TranscriptState {
  activeCallId: string | null
  isPlaying: boolean
  playbackPosition: number

  setActiveCallId: (id: string | null) => void
  setIsPlaying: (v: boolean) => void
  setPlaybackPosition: (pos: number) => void
}

export const useTranscriptStore = create<TranscriptState>()((set) => ({
  activeCallId: null,
  isPlaying: false,
  playbackPosition: 0,

  setActiveCallId: (activeCallId) => set({ activeCallId }),
  setIsPlaying: (isPlaying) => set({ isPlaying }),
  setPlaybackPosition: (playbackPosition) => set({ playbackPosition }),
}))
