// Phase 0 root page — redirects and dashboard implemented in Phase 2 (App Shell)
export default function RootPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-background">
      <div className="text-center">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">Karpathys</h1>
        <p className="mt-2 text-sm text-muted-foreground">Phase 0 — Foundation</p>
      </div>
    </main>
  )
}