# Karpathys operations dashboard

Next.js operator interface and FastAPI orchestration backend. The backend owns workflows, governance, approvals, calls, transcripts and events. REI voice and Bob planning are separate repositories/databases; call, lead and Sophia session IDs require explicit mapping.

See [audit and verification](docs/SYSTEM-AUDIT.md) and [test evidence](docs/test-evidence/system-audit). Frontend: `cd frontend`, `npm ci --ignore-scripts`, `npm run typecheck`, `npm run lint`, `npm test`, `npm run build`. Backend verification requires an explicitly disposable PostgreSQL database ending in `_test` and disposable Redis; test hooks reset its public schema. CI provisions these services without production credentials.

The verified repair pass does not establish a completed visual redesign, live phone behavior, full migration upgrades, or production readiness. Nothing deployed.
