'use client'

import { useQuery } from '@tanstack/react-query'
import { healthApi } from './api'

const KEYS = {
  health: () => ['health', 'liveness'] as const,
  ready: () => ['health', 'readiness'] as const,
  metrics: () => ['health', 'metrics'] as const,
}

// ── Queries ──────────────────────────────────────────────────────────────────

export function useHealth() {
  return useQuery({
    queryKey: KEYS.health(),
    queryFn: () => healthApi.health(),
    refetchInterval: 10_000,
  })
}

export function useReadiness() {
  return useQuery({
    queryKey: KEYS.ready(),
    queryFn: () => healthApi.ready(),
    refetchInterval: 30_000,
  })
}

export function useMetrics() {
  return useQuery({
    queryKey: KEYS.metrics(),
    queryFn: () => healthApi.metrics(),
    refetchInterval: 30_000,
  })
}
