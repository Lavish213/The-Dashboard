export default function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center">
        <h2 className="text-lg font-semibold text-foreground">404 — Not found</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          This page does not exist.
        </p>
      </div>
    </div>
  )
}