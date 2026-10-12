'use client'

import { useIsFetching } from '@tanstack/react-query'

export function RouteProgressBar() {
  const fetching = useIsFetching()
  if (!fetching) return null

  return (
    <div
      className="fixed top-0 left-0 z-50 h-0.5 bg-teal-400 transition-all duration-200 ease-out"
      role="progressbar"
      aria-label="Updating dashboard data"
      style={{ width: '100%' }}
    />
  )
}
