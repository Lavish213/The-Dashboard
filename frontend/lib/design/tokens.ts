/**
 * Karpathys Design Tokens — TypeScript
 * Source of truth for programmatic token access
 */

export const spacing = {
  0: '0px',
  1: '4px',
  2: '8px',
  3: '12px',
  4: '16px',
  5: '20px',
  6: '24px',
  8: '32px',
  10: '40px',
  12: '48px',
  16: '64px',
  20: '80px',
  24: '96px',
} as const

export const fontSize = {
  xs: '0.6875rem',   // 11px
  sm: '0.75rem',     // 12px
  base: '0.8125rem', // 13px
  md: '0.875rem',    // 14px
  lg: '1rem',        // 16px
  xl: '1.125rem',    // 18px
  '2xl': '1.25rem',  // 20px
  '3xl': '1.5rem',   // 24px
} as const

export const fontWeight = {
  normal: 400,
  medium: 500,
  semibold: 600,
  bold: 700,
} as const

export const radius = {
  xs: '2px',
  sm: '4px',
  md: '6px',
  lg: '8px',
  xl: '12px',
  '2xl': '16px',
  full: '9999px',
} as const

export const zIndex = {
  base: 0,
  raised: 10,
  dropdown: 100,
  sticky: 200,
  overlay: 300,
  modal: 400,
  toast: 500,
  tooltip: 600,
} as const

export const duration = {
  instant: 0,
  fast: 100,
  normal: 200,
  slow: 300,
  slower: 500,
} as const

export const easing = {
  in: 'cubic-bezier(0.4, 0, 1, 1)',
  out: 'cubic-bezier(0, 0, 0.2, 1)',
  inOut: 'cubic-bezier(0.4, 0, 0.2, 1)',
  spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
} as const

export const shadow = {
  xs: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
  sm: '0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)',
  md: '0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)',
  lg: '0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)',
  xl: '0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)',
} as const

export const layout = {
  sidebarWidth: '240px',
  sidebarCollapsed: '60px',
  headerHeight: '56px',
  panelMinWidth: '280px',
} as const

/** Operational status variants */
export const statusVariant = {
  active: 'active',
  pending: 'pending',
  failed: 'failed',
  paused: 'paused',
  escalated: 'escalated',
  completed: 'completed',
  cancelled: 'cancelled',
} as const

export type StatusVariant = keyof typeof statusVariant

/** Risk level variants */
export const riskLevel = {
  critical: 'critical',
  high: 'high',
  medium: 'medium',
  low: 'low',
} as const

export type RiskLevel = keyof typeof riskLevel
