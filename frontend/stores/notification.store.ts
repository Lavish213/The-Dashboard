import { create } from 'zustand'

export interface AppNotification {
  id: string
  title: string
  body?: string
  type: 'info' | 'success' | 'warning' | 'error'
  read: boolean
  href?: string
  createdAt: number
}

interface NotificationState {
  notifications: AppNotification[]
  unreadCount: number

  addNotification: (n: Omit<AppNotification, 'id' | 'read' | 'createdAt'>) => void
  markRead: (id: string) => void
  markAllRead: () => void
  removeNotification: (id: string) => void
  clearAll: () => void
}

export const useNotificationStore = create<NotificationState>()((set) => ({
  notifications: [],
  unreadCount: 0,

  addNotification: (n) =>
    set((s) => {
      const notification: AppNotification = {
        ...n,
        id: crypto.randomUUID(),
        read: false,
        createdAt: Date.now(),
      }
      const notifications = [notification, ...s.notifications].slice(0, 50)
      return {
        notifications,
        unreadCount: notifications.filter((x) => !x.read).length,
      }
    }),

  markRead: (id) =>
    set((s) => {
      const notifications = s.notifications.map((n) =>
        n.id === id ? { ...n, read: true } : n
      )
      return { notifications, unreadCount: notifications.filter((x) => !x.read).length }
    }),

  markAllRead: () =>
    set((s) => ({
      notifications: s.notifications.map((n) => ({ ...n, read: true })),
      unreadCount: 0,
    })),

  removeNotification: (id) =>
    set((s) => {
      const notifications = s.notifications.filter((n) => n.id !== id)
      return { notifications, unreadCount: notifications.filter((x) => !x.read).length }
    }),

  clearAll: () => set({ notifications: [], unreadCount: 0 }),
}))
