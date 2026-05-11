'use client'

/**
 * useApprovals — Phase 0 shell.
 * Approval queue query and mutation implemented in Phase 5.
 */
export function useApprovals() {
  return {
    approvals: [],
    loading: false,
    error: null,
    approve: async (_id: string) => {},
    reject: async (_id: string) => {},
  }
}
