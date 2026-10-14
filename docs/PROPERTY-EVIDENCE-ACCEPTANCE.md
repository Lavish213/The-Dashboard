# Property evidence acceptance — 2026-10-14

The properties search page now labels provider values as estimates rather than ARV. It no longer presents estimated value minus historical sale price as equity; actual loan payoff and lien evidence is required. The manual deal screen starts empty, requires explicit repairs, validates dollars/cents input and makes clear that financing, holding and closing costs are not included. No generated company offer or approved ARV is inferred from provider data.

Validation: TypeScript, production build, ESLint and 28 frontend regression tests pass. The coordinated REI dashboard additionally displays fresh bound Bob advisory prices, effective dates, reviewed-comp counts and adjusted sale spans, independently from saved appointments and offers. Bob-to-Sophia integration remains pinned to reviewed commits in coordinated CI. Live hosted data/feed/audio/email/calendar acceptance is not established by local tests.

The CRMLS source runner currently returns candidates, not persisted leads; provider credentials, canonical APN enrichment, dated closed sales and inspection/repair evidence remain required. No claim of all-site lead discovery, local ARV grade A or live 10/10 is made.
