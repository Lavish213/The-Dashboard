'use client'

/**
 * useTranscript — Phase 0 shell.
 * Live transcript streaming implemented in Phase 4.
 */
export function useTranscript(_callId?: string) {
  return {
    turns: [],
    loading: false,
    error: null,
  }
}
