# Dashboard repair design contract

## Enhancement contract: remaining wiring

Keep the inspected Settings layout, tabs and appearance control. Add an authenticated read-only server configuration query, real security lifetimes, admin-only paginated team roster, and an account-owned notification feed with unread filtering and acknowledged read actions. The server remains authoritative; no cosmetic preference is represented as a delivery policy. Separate voice configuration and external booking capabilities remain explicitly unavailable unless supplied by their actual service. Loading, error, empty, populated, permission-denied and mutation-pending states must be visible and typed.

Follow-ups query only scheduled leads; Calendar filters the selected month on the server; Deals totals aggregate the full matching set. All lists expose real pagination instead of an unreachable 200-record cap. Pagination errors retain existing records and never advertise an empty queue. Calendar items use keyboard-accessible links. Backend permissions and timezone validation are tested independently from synthetic UI fixtures.

Established after inspecting current-run desktop/mobile screenshots and WCAG checks, before UI changes. Existing architecture and data flows remain the foundation; the four-repository map and ten-product primary-source comparison are in REI-AGENT/docs/system-audit.

## Purpose and information hierarchy

An operator needs to understand current calls, assess pipeline performance, and reach approvals, follow-ups, and scheduled work quickly. Keep the existing navigation routes. Organize the dashboard into work shortcuts, live conversation status, operational metrics, and social activity. All metrics must come from authenticated backend queries; no invented trends, availability, provider configuration, or success indicators.

## Component structure

AppShellRuntime → accessible Topbar, grouped AppNav / titled MobileNav, main → PageContainer → dashboard sections (SophiaStatusWidget, KPIGrid, SocialWidget). Settings uses the authenticated user and real theme preference, with explicit unavailability for server configuration rather than local-only governance switches. The backend settings router currently contains no endpoints.

## Data and states

TanStack Query owns social fetching, cancellation, bounded retries and refresh intervals. Loading, successful zero, error without data, and error with stale data must remain distinct. Independent sources retain independently verified values. Live activity is based on the current session or connected call; missing connection data is unknown, not proof of readiness. API readiness is labeled separately from voice/provider readiness.

## Interactions and responsiveness

Every displayed control must perform its described action. Replace the dead notification button with an explicit approvals destination. Preserve command search, sidebar collapse, theme switching, navigation and backend operations. Single content scroll region; responsive header/actions and cards; no horizontal page overflow at 390px. Mobile menu has an accessible title, closes on selection, and preserves client navigation. Respect reduced-motion preference.

## Visual and accessibility rules

Preserve DM Sans / Playfair / DM Mono, dark/light tokens, teal accents and existing icon system. Increase title/description hierarchy and section spacing; remove faded navigation labels that measured 2.23:1 contrast. Controls have names, focus indication and readable text. Error text uses contrast-safe tokens. WCAG automated results are evidence for tested states, not a full accessibility certification.

## Verification boundaries

Run the actual production Next build in a fresh browser with synthetic API fixtures and no production calls. Save before/after screenshots, runtime errors, network requests, overflow measurements and axe findings. Test mobile navigation, sidebar collapse, command search, theme and Settings identity. Separately run typecheck, lint, build and API/store fault tests. Provider audio, deployment readiness, real user permissions and appointment execution remain integration gates, outside what fixture screenshots can prove.
