'use client'

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { transcriptsApi } from '../api'

const KEYS = {
  detail: (id: string) => ['transcripts', id] as const,
  chunks: (id: string, page: number) => ['transcripts', id, 'chunks', page] as const,
  events: (id: string) => ['transcripts', id, 'events'] as const,
  replay: (id: string) => ['transcripts', id, 'replay'] as const,
}

export function useTranscriptQuery(id: string) {
  return useQuery({
    queryKey: KEYS.detail(id),
    queryFn: () => transcriptsApi.get(id),
    enabled: !!id,
  })
}

export function useTranscriptChunks(id: string, page = 1) {
  return useQuery({
    queryKey: KEYS.chunks(id, page),
    queryFn: () => transcriptsApi.chunks(id, page),
    enabled: !!id,
  })
}

export function useTranscriptEvents(id: string) {
  return useQuery({
    queryKey: KEYS.events(id),
    queryFn: () => transcriptsApi.events(id),
    enabled: !!id,
  })
}

export function useTranscriptReplay(id: string) {
  return useQuery({
    queryKey: KEYS.replay(id),
    queryFn: () => transcriptsApi.replay(id),
    enabled: !!id,
  })
}

function useTranscriptMutation(action: (id: string) => Promise<unknown>) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: action,
    onSuccess: (_data, id) => {
      void qc.invalidateQueries({ queryKey: KEYS.detail(id) })
      void qc.invalidateQueries({ queryKey: KEYS.events(id) })
    },
  })
}

export function useStartTranscript() {
  return useTranscriptMutation(transcriptsApi.start)
}

export function usePauseTranscript() {
  return useTranscriptMutation(transcriptsApi.pause)
}

export function useResumeTranscript() {
  return useTranscriptMutation(transcriptsApi.resume)
}

export function useCompleteTranscript() {
  return useTranscriptMutation(transcriptsApi.complete)
}

export function useArchiveTranscript() {
  return useTranscriptMutation(transcriptsApi.archive)
}
