import { apiFetch } from '@/services/api'
import type { ContextPacket, TurnSignals } from '@/stores/sophia.store'

export type TransferReason =
  | 'trust_low'
  | 'hot_lead'
  | 'seller_requested'
  | 'ai_uncertain'
  | 'negotiation'
  | 'legal_concern'
  | 'operator_manual'

export interface InitiateHandoffResponse {
  session_id: string
  transfer_reason: string
  initiated_at: string
  context_packet: ContextPacket
}

export async function initiateHandoff(
  sessionId: string,
  turnId: string,
  transferReason: TransferReason = 'operator_manual',
  operatorUserId?: string,
): Promise<InitiateHandoffResponse> {
  return apiFetch<InitiateHandoffResponse>('/api/handoff/initiate', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      turn_id: turnId,
      transfer_reason: transferReason,
      operator_user_id: operatorUserId ?? null,
    }),
  })
}

export async function getContextPacket(sessionId: string): Promise<ContextPacket> {
  return apiFetch<ContextPacket>(`/api/handoff/${sessionId}/context`)
}

export async function getSignals(sessionId: string): Promise<TurnSignals> {
  return apiFetch<TurnSignals>(`/api/handoff/${sessionId}/signals`)
}

export async function acceptHandoff(
  sessionId: string,
  acceptedBy: string,
): Promise<{ session_id: string; status: string }> {
  return apiFetch(`/api/handoff/${sessionId}/accept`, {
    method: 'POST',
    body: JSON.stringify({ accepted_by: acceptedBy }),
  })
}

export async function rejectHandoff(
  sessionId: string,
  rejectedBy: string,
  reason: string,
): Promise<{ session_id: string; status: string }> {
  return apiFetch(`/api/handoff/${sessionId}/reject`, {
    method: 'POST',
    body: JSON.stringify({ rejected_by: rejectedBy, reason }),
  })
}

export async function logOutcome(
  sessionId: string,
  outcome: string,
  durationSeconds: number,
  appointmentSet: boolean,
  notes?: string,
): Promise<void> {
  await apiFetch(`/api/handoff/${sessionId}/outcome`, {
    method: 'POST',
    body: JSON.stringify({
      outcome,
      duration_seconds: durationSeconds,
      appointment_set: appointmentSet,
      notes: notes ?? null,
    }),
  })
}