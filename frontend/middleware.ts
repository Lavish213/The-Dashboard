import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

// Phase 0 shell — auth enforcement implemented in Phase 3
// This middleware is a passthrough until auth backend is established
export function middleware(_request: NextRequest) {
  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico|public/).*)',
  ],
}