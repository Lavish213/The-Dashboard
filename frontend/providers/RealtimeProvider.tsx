'use client'

// RealtimeProvider is a logical grouping layer — WebSocket lifecycle is in WebsocketProvider.
// This component is kept for layout composition; it requires WebsocketProvider as an ancestor.

import React from 'react'

export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
