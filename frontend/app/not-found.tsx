import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background">
      <div className="text-center">
        <p className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          404
        </p>
        <h2 className="mt-1 text-lg font-semibold text-foreground">
          Page not found
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          This route does not exist in the platform.
        </p>
      </div>
      <Link
        href="/dashboard"
        className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition-colors hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring"
      >
        Go to Dashboard
      </Link>
    </div>
  )
}