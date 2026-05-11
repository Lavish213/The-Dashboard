/**
 * Karpathys Motion System — Framer Motion variants
 * Operational motion: subtle, purposeful, reduced-motion-safe
 */
import type { Variants, Transition } from 'framer-motion'

// ─── Base transitions ─────────────────────────────────────────────────────────

export const transitionFast: Transition = {
  duration: 0.1,
  ease: [0, 0, 0.2, 1],
}

export const transitionNormal: Transition = {
  duration: 0.2,
  ease: [0, 0, 0.2, 1],
}

export const transitionSlow: Transition = {
  duration: 0.3,
  ease: [0, 0, 0.2, 1],
}

export const transitionSpring: Transition = {
  type: 'spring',
  stiffness: 400,
  damping: 30,
}

// ─── Fade variants ────────────────────────────────────────────────────────────

export const fadeVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: transitionNormal },
  exit: { opacity: 0, transition: transitionFast },
}

// ─── Slide variants ───────────────────────────────────────────────────────────

export const slideUpVariants: Variants = {
  hidden: { opacity: 0, y: 4 },
  visible: { opacity: 1, y: 0, transition: transitionNormal },
  exit: { opacity: 0, y: 4, transition: transitionFast },
}

export const slideDownVariants: Variants = {
  hidden: { opacity: 0, y: -4 },
  visible: { opacity: 1, y: 0, transition: transitionNormal },
  exit: { opacity: 0, y: -4, transition: transitionFast },
}

export const slideRightVariants: Variants = {
  hidden: { opacity: 0, x: -8 },
  visible: { opacity: 1, x: 0, transition: transitionNormal },
  exit: { opacity: 0, x: -8, transition: transitionFast },
}

export const slideLeftVariants: Variants = {
  hidden: { opacity: 0, x: 8 },
  visible: { opacity: 1, x: 0, transition: transitionNormal },
  exit: { opacity: 0, x: 8, transition: transitionFast },
}

// ─── Scale variants ───────────────────────────────────────────────────────────

export const scaleVariants: Variants = {
  hidden: { opacity: 0, scale: 0.96 },
  visible: { opacity: 1, scale: 1, transition: transitionNormal },
  exit: { opacity: 0, scale: 0.96, transition: transitionFast },
}

// ─── Sheet/drawer ─────────────────────────────────────────────────────────────

export const sheetVariants: Record<'left' | 'right' | 'top' | 'bottom', Variants> = {
  left: {
    hidden: { opacity: 0, x: '-100%' },
    visible: { opacity: 1, x: 0, transition: transitionNormal },
    exit: { opacity: 0, x: '-100%', transition: transitionFast },
  },
  right: {
    hidden: { opacity: 0, x: '100%' },
    visible: { opacity: 1, x: 0, transition: transitionNormal },
    exit: { opacity: 0, x: '100%', transition: transitionFast },
  },
  top: {
    hidden: { opacity: 0, y: '-100%' },
    visible: { opacity: 1, y: 0, transition: transitionNormal },
    exit: { opacity: 0, y: '-100%', transition: transitionFast },
  },
  bottom: {
    hidden: { opacity: 0, y: '100%' },
    visible: { opacity: 1, y: 0, transition: transitionNormal },
    exit: { opacity: 0, y: '100%', transition: transitionFast },
  },
}

// ─── List stagger ─────────────────────────────────────────────────────────────

export const listContainerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.04,
      delayChildren: 0.05,
    },
  },
}

export const listItemVariants: Variants = {
  hidden: { opacity: 0, y: 4 },
  visible: { opacity: 1, y: 0, transition: transitionFast },
}

// ─── Presence wrapper props ───────────────────────────────────────────────────

export const presenceProps = {
  initial: 'hidden',
  animate: 'visible',
  exit: 'exit',
} as const

// ─── Reduced motion fallback ──────────────────────────────────────────────────
// Use with useReducedMotion hook — pass noMotionVariants when reduced motion active

export const noMotionVariants: Variants = {
  hidden: { opacity: 1 },
  visible: { opacity: 1 },
  exit: { opacity: 1 },
}
