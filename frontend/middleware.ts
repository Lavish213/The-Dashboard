import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

/**
 * Phase 2 middleware — routing structure.
 *
 * Auth enforcement (JWT validation, RBAC) implemented in Phase 3.
 * Currently: passthrough with redirect for root → dashboard.
 *
 * Phase 3 will add:
 * - JWT token verification from Authorization header / cookie
 * - Redirect unauthenticated users to /login
 * - Role-based route protection
 */

const PUBLIC_ROUTES = [
  '/login',
  '/register',
  '/forgot-password',
  '/reset-password',
]

function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(route + '/')
  )
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl

  // Root redirect → dashboard
  if (pathname === '/') {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  // Phase 3: add authentication check here
  // const isAuthenticated = verifyToken(request)
  // if (!isAuthenticated && !isPublicRoute(pathname)) {
  //   return NextResponse.redirect(new URL('/login', request.url))
  // }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization)
     * - favicon.ico, sitemap.xml, robots.txt
     * - public folder assets
     */
    '/((?!_next/static|_next/image|favicon\\.ico|sitemap\\.xml|robots\\.txt|public/).*)',
  ],
}
