'use client'

import { useState } from 'react'
import { useSophiaStore } from '@/stores/sophia.store'
import { initiateHandoff } from '@/services/sophia'

interface TakeoverButtonProps {
  turnId: string
  onSuccess?: () => void
}

export function TakeoverButton({ turnId, onSuccess }: TakeoverButtonProps) {
  const { sessionId, isTransferring, setTransferring, setTransferError, setMode, setContextPacket } =
    useSophiaStore()
  const [confirmed, setConfirmed] = useState(false)

  async function handleTakeover() {
    if (!sessionId) return

    if (!confirmed) {
      setConfirmed(true)
      setTimeout(() => setConfirmed(false), 3000)
      return
    }

    setTransferring(true)
    setTransferError(null)

    try {
      const result = await initiateHandoff(sessionId, turnId, 'operator_manual')
      setContextPacket(result.context_packet)
      setMode('human_takeover')
      onSuccess?.()
    } catch (err) {
      setTransferError(err instanceof Error ? err.message : 'Transfer failed')
    } finally {
      setTransferring(false)
      setConfirmed(false)
    }
  }

  return (
    <button
      onClick={handleTakeover}
      disabled={isTransferring || !sessionId}
      className={`w-full rounded-md px-4 py-2.5 text-sm font-semibold transition-all disabled:opacity-50 ${
        confirmed
          ? 'animate-pulse border border-red-500/40 bg-red-500/20 text-red-300'
          : 'border border-amber-500/25 bg-amber-500/10 text-amber-400 hover:bg-amber-500/20'
      }`}
    >
      {isTransferring
        ? 'Transferring…'
        : confirmed
          ? 'Tap again to confirm takeover'
          : 'Take Over Call'}
    </button>
  )
}