/**
 * Layout persistence helpers.
 * Zustand persist middleware handles sidebar/panel via localStorage automatically.
 * These utilities handle edge cases and hydration safety.
 */

const STORAGE_KEY = 'karpathys:layout'

interface PersistedLayout {
  sidebarCollapsed: boolean
  panelWidth: number
}

const DEFAULTS: PersistedLayout = {
  sidebarCollapsed: false,
  panelWidth: 420,
}

/** Safe read during SSR — returns defaults when window is unavailable */
export function readPersistedLayout(): PersistedLayout {
  if (typeof window === 'undefined') return DEFAULTS
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULTS
    return { ...DEFAULTS, ...JSON.parse(raw) }
  } catch {
    return DEFAULTS
  }
}

export function writePersistedLayout(layout: Partial<PersistedLayout>): void {
  if (typeof window === 'undefined') return
  try {
    const current = readPersistedLayout()
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...current, ...layout }))
  } catch {
    // Storage write failed — silent (quota exceeded, private browsing)
  }
}

/** Clamps panel width to valid range */
export function clampPanelWidth(width: number): number {
  return Math.max(280, Math.min(800, width))
}

/** Clamps sidebar width to valid range */
export function clampSidebarWidth(width: number): number {
  return Math.max(200, Math.min(400, width))
}
