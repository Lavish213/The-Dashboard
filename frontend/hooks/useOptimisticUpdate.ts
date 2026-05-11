import { useState, useCallback } from 'react'

interface UseOptimisticUpdateReturn<T> {
  data: T
  isPending: boolean
  /** Apply optimistic update immediately; rollback on error */
  update: (optimistic: T, mutation: () => Promise<T>) => Promise<void>
  rollback: () => void
}

/**
 * Manages optimistic UI updates with automatic rollback on mutation failure.
 */
export function useOptimisticUpdate<T>(initialData: T): UseOptimisticUpdateReturn<T> {
  const [data, setData] = useState<T>(initialData)
  const [snapshot, setSnapshot] = useState<T>(initialData)
  const [isPending, setIsPending] = useState(false)

  const rollback = useCallback(() => {
    setData(snapshot)
    setIsPending(false)
  }, [snapshot])

  const update = useCallback(
    async (optimistic: T, mutation: () => Promise<T>) => {
      setSnapshot(data)
      setData(optimistic)
      setIsPending(true)
      try {
        const result = await mutation()
        setData(result)
      } catch {
        setData(snapshot)
      } finally {
        setIsPending(false)
      }
    },
    [data, snapshot]
  )

  return { data, isPending, update, rollback }
}
