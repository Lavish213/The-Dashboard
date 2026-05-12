'use client'

import { useQuery } from '@tanstack/react-query'
import { auditApi } from './api'
import type { AuditFilters } from './api'

const KEYS = {
  list: (filters: AuditFilters, page: number, pageSize: number) =>
    ['audit', 'list', filters, page, pageSize] as const,
  correlation: (correlationId: string, page: number, pageSize: number) =>
    ['audit', 'correlation', correlationId, page, pageSize] as const,
}

// ── Queries ──────────────────────────────────────────────────────────────────

export function useAuditTimeline(filters: AuditFilters, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: KEYS.list(filters, page, pageSize),
    queryFn: () => auditApi.list(filters, page, pageSize),
  })
}

export function useCorrelationTimeline(correlationId: string, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: KEYS.correlation(correlationId, page, pageSize),
    queryFn: () => auditApi.correlation(correlationId, page, pageSize),
    enabled: !!correlationId,
  })
}
