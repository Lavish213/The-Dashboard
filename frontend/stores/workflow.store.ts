import { create } from 'zustand'

/**
 * Workflow store — Phase 2 shell.
 * Workflow state machine and execution tracking implemented in Phase 5.
 */

interface WorkflowState {
  activeWorkflowId: string | null
  setActiveWorkflowId: (id: string | null) => void
}

export const useWorkflowStore = create<WorkflowState>()((set) => ({
  activeWorkflowId: null,
  setActiveWorkflowId: (activeWorkflowId) => set({ activeWorkflowId }),
}))
