import { create } from 'zustand'

/**
 * Approval store — Phase 2 shell.
 * Approval queue, risk display, and audit rails implemented in Phase 7.
 */

interface ApprovalState {
  pendingCount: number
  setPendingCount: (n: number) => void
}

export const useApprovalStore = create<ApprovalState>()((set) => ({
  pendingCount: 0,
  setPendingCount: (pendingCount) => set({ pendingCount }),
}))
