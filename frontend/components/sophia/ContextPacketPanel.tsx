'use client'

import { useSophiaStore } from '@/stores/sophia.store'

export function ContextPacketPanel() {
  const packet = useSophiaStore((s) => s.contextPacket)

  if (!packet) return null

  return (
    <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 space-y-4">
      <div className="flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-amber-400" />
        <span className="text-xs font-semibold uppercase tracking-widest text-amber-400">
          Seller Brief
        </span>
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        {packet.seller_name && (
          <div>
            <p className="text-muted-foreground">Name</p>
            <p className="font-medium text-foreground mt-0.5">{packet.seller_name}</p>
          </div>
        )}
        {packet.address && (
          <div>
            <p className="text-muted-foreground">Address</p>
            <p className="font-medium text-foreground mt-0.5">{packet.address}</p>
          </div>
        )}
        {packet.motivation && (
          <div>
            <p className="text-muted-foreground">Motivation</p>
            <p className="font-medium text-teal-400 mt-0.5">{packet.motivation}</p>
          </div>
        )}
        {packet.timeline && (
          <div>
            <p className="text-muted-foreground">Timeline</p>
            <p className="font-medium text-foreground mt-0.5">{packet.timeline}</p>
          </div>
        )}
        {packet.emotional_state && (
          <div>
            <p className="text-muted-foreground">Emotional state</p>
            <p className="font-medium text-foreground mt-0.5">{packet.emotional_state}</p>
          </div>
        )}
        <div>
          <p className="text-muted-foreground">Deal heat</p>
          <p className="font-medium text-foreground mt-0.5">{packet.deal_heat.toFixed(1)} / 10</p>
        </div>
      </div>

      {packet.objections_raised.length > 0 && (
        <div>
          <p className="text-xs text-muted-foreground mb-1.5">Objections raised</p>
          <div className="flex flex-wrap gap-1.5">
            {packet.objections_raised.map((obj, i) => (
              <span
                key={i}
                className="rounded border border-red-500/20 bg-red-500/10 px-2 py-0.5 text-xs text-red-400"
              >
                {obj}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="rounded border border-border bg-card p-3">
        <p className="text-xs text-muted-foreground mb-1">Sophia's summary</p>
        <p className="text-xs text-foreground leading-relaxed">{packet.sophia_summary}</p>
      </div>
    </div>
  )
}