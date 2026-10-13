'use client'

import { useInfiniteQuery } from '@tanstack/react-query'
import { apiFetch } from '@/services/api'

interface LeadPage<T> {
  items: T[]
  total: number
  page: number
  total_pages: number
  summary: { by_status: Record<string, number>; average_score: number; score_total: number } | null
}

export function useLeadPages<T>(filters: Record<string, string>) {
  return useInfiniteQuery({
    queryKey: ['leads', 'collection', filters],
    initialPageParam: 1,
    queryFn: ({ pageParam, signal }) => {
      const params = new URLSearchParams({ ...filters, page: String(pageParam), page_size: '200' })
      return apiFetch<LeadPage<T>>(`/api/v1/leads?${params}`, { signal })
    },
    getNextPageParam: last => last.page < last.total_pages ? last.page + 1 : undefined,
  })
}
