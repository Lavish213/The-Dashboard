/**
 * SkipNav — accessibility skip-to-content link.
 * Visually hidden until focused; keyboard users can skip navigation.
 * Must be the first focusable element in the DOM.
 */
export function SkipNav() {
  return (
    <a
      href="#main-content"
      className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[9999] focus:rounded-md focus:bg-primary focus:px-4 focus:py-2 focus:text-sm focus:font-medium focus:text-primary-foreground focus:outline-none focus:ring-2 focus:ring-ring"
    >
      Skip to main content
    </a>
  )
}
