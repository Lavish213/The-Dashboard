'use client'

import { useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'

export function RouteProgressBar() {
  const pathname = usePathname()
  const [loading, setLoading] = useState(false)
  const [width, setWidth] = useState(0)

  useEffect(() => {
    setLoading(true)
    setWidth(30)
    const t1 = setTimeout(() => setWidth(60), 100)
    const t2 = setTimeout(() => setWidth(85), 200)
    const t3 = setTimeout(() => {
      setWidth(100)
      setTimeout(() => {
        setLoading(false)
        setWidth(0)
      }, 200)
    }, 350)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
      clearTimeout(t3)
    }
  }, [pathname])

  if (!loading && width === 0) return null

  return (
    <div
      className="fixed top-0 left-0 z-50 h-0.5 bg-teal-400 transition-all duration-200 ease-out"
      style={{ width: `${width}%`, opacity: loading ? 1 : 0 }}
    />
  )
}