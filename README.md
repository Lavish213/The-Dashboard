# Karpathys operations dashboard

Next.js operator interface and FastAPI orchestration backend. The backend owns workflows, governance, approvals, calls, transcripts and events. REI voice, standalone Sophia and Bob planning are separate repositories/databases; external lead, provider call and Sophia session identities require explicit mapping.

See [audit and verification](docs/SYSTEM-AUDIT.md), [screenshot audit](docs/visual-audit/REPORT.md) and the coordinated master log in REI-AGENT `docs/system-audit`.

Frontend: `cd frontend`, `npm ci --ignore-scripts`, `npm run typecheck`, `npm run lint`, `npm test`, `npm run build`. `npm run test:browser` starts the actual production frontend with synthetic API fixtures; it prevents external actions. Backend CI provisions disposable PostgreSQL and Redis. Local SQL testing requires explicit loopback `TEST_DATABASE_URL` ending in `_test` and a disposable Redis; test hooks reset the public schema. Never use existing data. The actual REI producer contract requires `REI_REPO` pointing to the coordinated checkout; CI pins that revision.

## Production configuration

Requires Docker Compose 2.24.4 or later. Set `.env.production` with `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `REDIS_PASSWORD`, `SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `CORS_ORIGINS`, `DOMAIN` and required provider credentials. Database/Redis URLs must use the configured credentials and internal service names. Keep secrets outside git. `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL` default to the browser origin; configured values are passed at build time and require rebuilding after changes.

Validate before deployment: `docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml config --quiet`. Only the proxy exposes public ports; application source mounts and inherited development environment values are removed. Production backend startup initializes only an empty schema from the frozen snapshot and verifies its exact model shape/head. Existing drift fails closed; it requires a reviewed data migration, backup and rollback plan. This does not prove all historical migrations upgrade arbitrary existing databases. `python scripts/verify-production-compose.py` validates the overlay using synthetic credentials without deployment.

Deploy dashboard frontend/backend together: socket authentication now requires a fresh, single-use ticket from authenticated `POST /api/v1/auth/ws-ticket`; raw JWT query connections are rejected. Tickets expire within 20 seconds, are atomically consumed in Redis, and resolve current active database roles.

The repair passes have verified code, synthetic browser interactions, disposable SQL persistence and configuration rendering. Real calls, audio quality, provider outages, approved action execution, external calendar reservations, durable event delivery and production operations remain separate acceptance gates. Nothing deployed.
