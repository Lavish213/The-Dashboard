'use client'

/**
 * useWorkflow — Phase 0 shell.
 * Workflow execution and status polling implemented in Phase 5.
 */
export function useWorkflow(_workflowId?: string) {
  return {
    workflow: null,
    loading: false,
    error: null,
    trigger: async () => {},
    pause: async () => {},
    resume: async () => {},
  }
}
