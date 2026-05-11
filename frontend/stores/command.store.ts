import { create } from 'zustand'

export interface RecentEntity {
  id: string
  type: 'lead' | 'property' | 'workflow' | 'call' | 'transcript'
  label: string
  href: string
  visitedAt: number
}

interface CommandState {
  open: boolean
  query: string
  recentEntities: RecentEntity[]

  setOpen: (open: boolean) => void
  toggleOpen: () => void
  setQuery: (query: string) => void
  addRecentEntity: (entity: Omit<RecentEntity, 'visitedAt'>) => void
  clearRecent: () => void
}

export const useCommandStore = create<CommandState>()((set) => ({
  open: false,
  query: '',
  recentEntities: [],

  setOpen: (open) => set({ open, query: open ? '' : '' }),
  toggleOpen: () => set((s) => ({ open: !s.open, query: '' })),
  setQuery: (query) => set({ query }),

  addRecentEntity: (entity) =>
    set((s) => {
      const without = s.recentEntities.filter((e) => e.id !== entity.id)
      const next = [{ ...entity, visitedAt: Date.now() }, ...without].slice(0, 10)
      return { recentEntities: next }
    }),

  clearRecent: () => set({ recentEntities: [] }),
}))
