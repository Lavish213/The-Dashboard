import { create } from 'zustand'
import type { Approval } from '@/types/approval'

interface ApprovalState {
  pendingCount: number
  // Operator-facing queue — populated by realtime events, server is source of truth
  pendingItems: Approval[]

  setPendingCount: (n: number) => void
  upsertPendingItem: (approval: Approval) => void
  removePendingItem: (approvalId: string) => void
  clearPendingItems: () => void
}

export const useApprovalStore = create<ApprovalState>()((set) => ({
  pendingCount: 0,
  pendingItems: [],

  setPendingCount: (pendingCount) => set({ pendingCount }),

  upsertPendingItem: (approval) =>
    set((s) => {
      const idx = s.pendingItems.findIndex((a) => a.id === approval.id)
      if (idx >= 0) {
        const next = [...s.pendingItems]
        next[idx] = approval
        return { pendingItems: next }
      }
      return { pendingItems: [approval, ...s.pendingItems] }
    }),

  removePendingItem: (approvalId) =>
    set((s) => ({
      pendingItems: s.pendingItems.filter((a) => a.id !== approvalId),
    })),

  clearPendingItems: () => set({ pendingItems: [] }),
}))
