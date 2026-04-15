# Pitfalls Research

**Domain:** IaC Visualization SaaS — CLI-to-SaaS transition for developer tooling
**Researched:** 2026-04-15
**Confidence:** HIGH (grounded in codebase analysis + known CLI-to-SaaS patterns)

---

## Critical Pitfalls

### Pitfall 1: CLI Auth Token Stored Insecurely, Breaking Enterprise Adoption

**What goes wrong:**
The `login` command writes an API token to a local config file (e.g., `~/.infracanvas/config.json` or `.infracanvas.yml`) without regard for OS credential stores. Enterprise users hit security review blocks — their CI/CD policies flag plaintext tokens in config files. Individual users accidentally commit the token to version control when `.infracanvas.yml` is project-scoped rather than user-scoped.

**Why it happens:**
Quickest path to a working `login` command is writing a JSON file to a config directory. Developers solve their own problem (local dev) and defer "do it right" to later. Later never comes.

**How to avoid:**
Use OS keychain integrations from day one: macOS Keychain, Linux libsecret (via `keyring` Python package), Windows Credential Manager. The `keyring` library (`pip install keyring`) abstracts all three. Store only a token reference in config files, never the token value itself. For CI/CD, support `INFRACANVAS_API_KEY` environment variable as the authoritative override (no disk write at all).

**Warning signs:**
- `login` command writes anything sensitive to a file path ending in `.yml`, `.json`, `.toml`
- No mention of `keyring` or env var fallback in the `push` command implementation
- Users asking "where is my token stored?" in GitHub issues

**Phase to address:**
CLI auth implementation phase (when building `login` and `push` commands). Cannot be retrofitted without breaking existing users' stored tokens.

---

### Pitfall 2: Viewer Code Diverges Between CLI HTML Export and SaaS Dashboard

**What goes wrong:**
The React viewer (`viewer/`) starts as a single-file HTML export. When the SaaS dashboard is built, someone creates a new React component that duplicates viewer logic for the "live" dashboard view. Security findings render differently in the CLI export vs. the web dashboard. Bug fixes to one don't propagate to the other. In 6 months you have two rendering paths with different behavior for the same data.

**Why it happens:**
The existing viewer is Vite-built as a standalone bundle injected via `window.__INFRACANVAS_DATA__`. The SaaS dashboard is a Next.js app. These feel like different contexts so developers build separately rather than extracting a shared package.

**How to avoid:**
Extract `viewer/src/` into a shared library (`packages/infracanvas-viewer`) before starting SaaS work. The library exports a `<InfracanvasViewer graph={...} />` React component that takes `graph` as a prop instead of reading from `window`. Both the HTML export (Vite bundle) and the Next.js dashboard import from this package. This is a monorepo boundary decision that must be made before SaaS development starts — changing it later requires coordinated rewrites.

**Warning signs:**
- "Fixed in SaaS dashboard but not CLI export" appearing in commit messages
- Separate `components/DiagramCanvas.tsx` files in both `viewer/` and `apps/web/`
- Security finding display logic copy-pasted across two directories

**Phase to address:**
Before any SaaS frontend work begins — must be the first architectural decision of the SaaS milestone.

---

### Pitfall 3: Scan Artifact Storage Schema Locked In Too Early

**What goes wrong:**
Scan results are stored as JSON blobs in Supabase Storage (object storage). When scan comparison, history diffing, and point-in-time diagram viewing are added in later phases, the team discovers the blob structure does not support efficient retrieval of specific fields (e.g., "show me just the security findings for scan X"). Every query loads the entire blob, then filters in application code. At scale (user with 500 scans), this becomes a performance and cost problem.

**Why it happens:**
First instinct is to store `json.dumps(scan_result)` as a single artifact. It works immediately. The structural inadequacy only becomes visible when building the history timeline and comparison features.

**How to avoid:**
Design the scan storage schema with all known downstream features in mind before writing a single migration. The schema must support: (1) metadata queryable in PostgreSQL (timestamp, resource count, finding count by severity, security score), (2) full graph JSON in Supabase Storage for viewer rendering, (3) security findings indexable by resource ID for comparison diffs. Store metadata in a `scans` table with foreign keys to `projects` and `users`, store the graph blob as a Storage object with a reference key in the `scans` table. Never store the full blob in the database column.

**Warning signs:**
- Migration that adds a column to `scans` table to store `findings_json` text after initial schema is live
- API endpoints loading full scan blob to return only the scan score
- No `scans` table — only an `artifacts` bucket in Supabase Storage

**Phase to address:**
Database schema design phase — must be finalized before the first `/push` API endpoint is implemented.

---

### Pitfall 4: Injected Window Data Becomes an XSS Vector in SaaS

**What goes wrong:**
The existing viewer reads from `window.__INFRACANVAS_DATA__` without validation (confirmed in CONCERNS.md: `viewer/src/App.tsx` lines 15-16). In the CLI export context this is acceptable — data comes from the user's own scan. In the SaaS context, this data comes from a server API. If the Next.js page injects server data into the page without sanitization, an XSS vector opens: a malicious scan result with script content in resource names or attribute values could execute in other users' browsers on the shared SaaS domain.

**Why it happens:**
The injection pattern is copy-pasted from the CLI export without reconsidering the trust model. In SaaS, the data origin is different — it was stored by a different user, potentially with adversarial content.

**How to avoid:**
In the SaaS context, pass graph data through React props (server-side rendered or fetched via API) rather than window injection. Add input validation at the FastAPI layer: resource names and attribute values must be strings within length limits, no HTML or script content. Add Content Security Policy headers in the Next.js middleware. The `window.__INFRACANVAS_DATA__` pattern should only exist in the CLI HTML export path.

**Warning signs:**
- Next.js `_document.tsx` or a page file using raw HTML injection to embed scan data
- No CSP headers in `next.config.js` or middleware
- Shared viewer component reading from `window` instead of props

**Phase to address:**
SaaS viewer integration phase, before any public sharing feature is enabled.

---

### Pitfall 5: Stripe Webhook Handling Done After Billing UI is Built

**What goes wrong:**
The billing integration adds Stripe checkout and shows a "Pro" badge in the dashboard. But Stripe webhook handling (subscription created, payment failed, subscription cancelled, trial ended) is left as a follow-up. Users subscribe, their payment fails on month 2, their account still has Pro access because the webhook handler was never built. Churn through failed payments goes undetected.

**Why it happens:**
The happy path (user subscribes, sees Pro features) is built and demoed. Webhooks feel like edge cases. They get added "in the next sprint." For a solo founder, that sprint keeps getting pushed.

**How to avoid:**
Treat webhook handling as part of the billing feature definition, not a separate task. Before shipping Stripe checkout, implement handlers for at minimum: `customer.subscription.created`, `customer.subscription.deleted`, `invoice.payment_failed`, `invoice.payment_succeeded`. Use Stripe CLI for local webhook testing during development. Store subscription status in the `users` table and check it on every Pro-gated API request — never trust client-side `isPro` state.

**Warning signs:**
- Billing feature marked complete with only checkout implemented
- Pro feature access checked by reading a hardcoded value rather than querying `subscription_status` from the database
- No `stripe listen` step in the local development setup instructions

**Phase to address:**
Billing integration phase. Webhooks are acceptance criteria for the billing feature, not an optional add-on.

---

### Pitfall 6: CLI `push` Command Couples Scan Format to API Version

**What goes wrong:**
The CLI sends scan results to the FastAPI backend in a format that matches the internal Python data structures (Pydantic models). When the API evolves — new fields, renamed keys, restructured findings — the CLI breaks for users on older versions. Because the CLI is pip-installed and users do not auto-update, you end up supporting multiple API versions simultaneously or breaking all CLI users on every backend deploy.

**Why it happens:**
The first `push` implementation serializes whatever `scan_result` returns directly to JSON and POSTs it. No versioning is designed because there is only one version at launch.

**How to avoid:**
Version the push API from day one: `/api/v1/scans`. Design a stable, documented `ScanPayload` schema that is the CLI's external contract. The FastAPI endpoint validates against this schema (Pydantic), not against internal models. Maintain this schema separately from internal data structures. When internals change, adapt the v1 endpoint rather than changing the schema. Add `cli_version` and `payload_version` fields to every push request so the API can handle migration logic later.

**Warning signs:**
- Push endpoint path without version prefix: `POST /api/scans`
- `ScanPayload` Pydantic model imported directly from internal scanning modules
- No documented schema for the push payload

**Phase to address:**
CLI `push` command implementation phase. API versioning must be in the initial design.

---

### Pitfall 7: Auth Session Not Propagated Correctly Across Next.js and FastAPI

**What goes wrong:**
The auth provider (Supabase Auth or Clerk) issues a JWT. The Next.js frontend reads this correctly via the auth SDK. But the FastAPI backend must independently verify the JWT on every API request. A common mistake: the Next.js server-side routes forward requests to FastAPI without including the `Authorization: Bearer <token>` header. FastAPI cannot verify the user, falls back to anonymous access, and either returns 401s or (worse) silently serves unscoped data.

**Why it happens:**
Developers test the frontend and backend separately. The Next.js pages work (auth SDK handles sessions). The FastAPI endpoints are tested with Postman using manually pasted tokens. The integration — Next.js server-side code forwarding auth headers to FastAPI — is never explicitly tested as a unit.

**How to avoid:**
Write an integration test on day one that: (1) authenticates a test user with Supabase/Clerk, (2) calls a Next.js API route that proxies to FastAPI, (3) verifies FastAPI returns scoped data for that user. FastAPI should use a dependency (`get_current_user`) that extracts and verifies the JWT on every protected endpoint. Never trust user ID from request body — always derive it from the verified JWT.

**Warning signs:**
- FastAPI endpoint that accepts `user_id` as a request body field rather than deriving it from the JWT
- Next.js server component that calls FastAPI with `fetch(url)` without attaching the session token
- Auth works in the browser but API calls from server components return 401

**Phase to address:**
Auth infrastructure phase — must be proven before any data endpoints are built.

---

### Pitfall 8: Silent Failures From Existing Codebase Become User Trust Failures in SaaS

**What goes wrong:**
CONCERNS.md documents that the HCL parser silently swallows exceptions and the config file silently ignores validation errors. These are acceptable annoyances in a CLI where the user sees some output. In SaaS, a scan that silently skips 30% of files appears to succeed — the user sees a diagram and security score. They trust it. In reality, the scan is incomplete. A user relying on the security score to gate a deployment misses critical findings. This is a trust-destroying incident.

**Why it happens:**
Known tech debt is deprioritized in favor of building new SaaS features. The assumption is "users know it is a CLI tool." SaaS users have different expectations — a web dashboard implies production quality.

**How to avoid:**
Fix all silent failure modes before the first SaaS scan can be processed: (1) HCL parser must log which files failed and why, (2) config validation errors must surface to the user, (3) scan results must include a `parse_warnings` field that the SaaS dashboard displays prominently. The dashboard should show "X files could not be parsed — results may be incomplete" rather than a clean success state. Treat this as blocking for SaaS launch.

**Warning signs:**
- `cli/infracanvas/parser/hcl.py` still has `except Exception: return` patterns when SaaS milestone starts
- FastAPI `/push` endpoint stores scan results without checking for `parse_warnings`
- SaaS dashboard shows a green checkmark for scans with parser failures

**Phase to address:**
Bug fix phase before SaaS milestone begins — must be resolved as pre-work.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hardcode `us-east-1` pricing in SaaS cost display | Avoid building region detection | Cost estimates for 60%+ of user infrastructure are wrong; user complaints and churn | Never in SaaS — users pay for accurate data |
| Store Stripe `price_id` as a string constant in code | Simple to ship | Adding new tiers requires code deploy, not config change | Acceptable for MVP with exactly 2 tiers; unacceptable if tiers change often |
| Use Supabase Storage public bucket for scan artifacts | Zero auth code on storage layer | Any user can read any scan artifact if they guess the path | Never — storage must be private with signed URLs |
| Single Supabase project for dev and prod | No setup overhead | A bad migration in dev destroys prod data | Never — always separate Supabase projects for dev/prod |
| Skip idempotency on `/push` endpoint | Simpler implementation | CLI retry on network failure creates duplicate scans | MVP acceptable if CLI has no retry logic; must fix before adding CI/CD webhooks |
| Use Next.js API routes as a pass-through proxy to FastAPI | Single auth surface, avoids CORS | Adds latency; both services must run locally | Acceptable pattern for SaaS; simplifies auth header forwarding |
| JWT verification as middleware in FastAPI rather than per-endpoint decorator | Less code, automatic coverage | Easy to forget to apply to new routers | Middleware approach is actually preferred — less risk than decorator-per-endpoint |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Supabase Auth + FastAPI | FastAPI tries to verify Supabase JWT with wrong secret (service role key instead of JWT secret) | Verify JWT using Supabase JWT secret from project settings, not the service role key; use `python-jose` or `PyJWT` |
| Supabase Storage + signed URLs | Generating signed URLs server-side that expire in 60 seconds, causing viewer to break mid-session | Generate signed URLs with at least 1-hour expiry for viewer sessions; regenerate on scan page load |
| Stripe + Supabase | Storing Stripe `customer_id` only in Stripe metadata, not in the `users` table | Always write `stripe_customer_id` to `users` table on `customer.created` webhook — Stripe metadata is not a database |
| Clerk/Supabase Auth + CLI | CLI `login` flow uses browser OAuth redirect but the CLI has no web server to receive the redirect | Implement device authorization flow (device code grant) or use API key generation in the dashboard that users paste into CLI |
| ReactFlow + scan artifacts from API | Loading full scan graph JSON directly into ReactFlow state causes re-renders on every polling tick | Stabilize graph identity with `useMemo` keyed on scan ID, not the full graph object |
| FastAPI + Supabase | Using Supabase Python client for database queries in an async FastAPI app | Supabase Python client is synchronous; use `asyncpg` or SQLAlchemy async for non-blocking FastAPI performance |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Loading full scan graph JSON to render scan list (history page) | History page slow; 10MB+ transferred for a 20-row list | Store metadata (resource count, finding count, score, timestamp) in `scans` table columns; load blob only for viewer | At ~20 scans per user |
| No pagination on `/api/projects/{id}/scans` | Memory spike on server; client freezes loading large lists | Always paginate with `?limit=20&cursor=<scan_id>` | At ~50 scans per project |
| Synchronous HCL parsing in FastAPI request handler | API request blocks for 30+ seconds on large Terraform repos | Parse in a background task (FastAPI `BackgroundTasks` or Celery); return `scan_id` immediately, poll for status | On any project with >100 .tf files |
| ReactFlow re-renders entire graph on filter change | Viewer sluggish with >200 nodes | Separate node visibility (opacity) from node re-creation; only recompute layout on structural changes | At ~200 nodes in the graph (confirmed O(n2) in CONCERNS.md) |
| Supabase Realtime for scan status polling | WebSocket overhead for a feature used once per scan | Use simple HTTP polling with exponential backoff; Realtime is overkill for this pattern | At ~100 concurrent users |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Serving scan artifacts from a public Supabase Storage bucket | Any user who guesses the path can read any customer's Terraform resource structure, including sensitive attribute values | Always use private buckets with RLS policies; generate signed URLs server-side with short expiry |
| Trusting `user_id` from JWT `sub` without checking project membership | User A can read User B's scans by knowing the scan ID | Every data query must enforce ownership: `WHERE project.user_id = current_user_id`; never accept scan IDs without ownership verification |
| Storing Terraform plan JSON verbatim in Supabase | Plan JSON may contain sensitive values (AWS account IDs, ARNs, resource attributes that may include connection strings) | Scrub sensitive fields before storage; filter known-sensitive attribute names from plan before persisting |
| Share links with sequential or predictable IDs | Enumeration attack exposes all shared diagrams | Use UUID v4 or a 32-character random slug for share link identifiers; never use integer IDs |
| API keys in CLI config files world-readable | Other processes or users on shared machines can read tokens | Store tokens with `keyring`; if writing to file, set `chmod 600` on creation |
| No rate limiting on `/push` endpoint | A buggy CI/CD pipeline floods the database with duplicate scans | Rate limit by API key: max 60 pushes per hour; return `429` with `Retry-After` header |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing a success state for scans with parse warnings | User trusts incomplete security scores; makes decisions on partial data | Show a "Scan incomplete" banner with a count of skipped files and a link to troubleshooting docs |
| Requiring users to run `infracanvas push` separately from `scan` | Friction breaks CI/CD adoption; users forget to push | Add `--push` flag to `scan` command: `infracanvas scan . --push` combines scan and upload in one command |
| Sharing a view link that requires the recipient to sign up | Share links lose value; IaC security reviews happen with external stakeholders | Shared diagram links must be fully accessible without login; add optional password protection, not a login requirement |
| No indication of scan freshness on the dashboard | Users do not know if the diagram reflects current infrastructure | Show "Last scanned: 3 days ago" with a visual age indicator; highlight if scan is older than 7 days |
| Scan comparison UI built without zoom synchronization | Side-by-side diffs are unusable if both scans are 500-node graphs | Link zoom/pan state between comparison panels; highlight only changed nodes by default, fade unchanged ones |

---

## "Looks Done But Isn't" Checklist

- [ ] **CLI `login` command:** Token stored securely via keyring or env var — verify no plaintext token in any config file on disk
- [ ] **CLI `push` command:** Payload schema is versioned — verify endpoint is `/api/v1/scans`, not `/api/scans`
- [ ] **Stripe billing:** Webhook handlers for `payment_failed` and `subscription.deleted` implemented — verify by simulating failed payment with Stripe CLI
- [ ] **Scan storage:** Metadata queryable in PostgreSQL without loading the artifact blob — verify history page loads in under 200ms for a user with 50 scans
- [ ] **Share links:** Accessible without login, with no sequential or predictable ID — verify by opening share link in incognito; verify ID is UUID or random slug
- [ ] **FastAPI auth:** Every protected endpoint derives `user_id` from JWT, not from request body — verify by sending a valid JWT for User A with `user_id` of User B in the body; confirm User A's data is returned
- [ ] **Supabase Storage:** Scan artifact bucket is private — verify by attempting to access a storage URL directly without a signed URL
- [ ] **Parse failures surfaced:** SaaS dashboard shows warning when scan has skipped files — verify by pushing a scan that includes a malformed .tf file
- [ ] **Viewer code shared:** Only one `DiagramCanvas` component exists in the codebase — verify no viewer logic is duplicated in `apps/web/`

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Viewer code diverged between CLI and SaaS | HIGH | Audit diff between both implementations; merge into shared package; update both consumers; regression test HTML export |
| Scan artifact schema locked in wrong structure | HIGH | Write migration script to re-process existing scan blobs; add metadata columns to `scans` table; backfill from blobs; update all API endpoints |
| Token stored in plaintext config file | MEDIUM | Release CLI update that reads existing config, migrates to keyring, deletes plaintext file; announce migration in release notes |
| Public Supabase storage bucket discovered | HIGH | Immediately set bucket to private; audit access logs; notify affected users; issue signed URLs for all active share links |
| Stripe webhooks never implemented | MEDIUM | Implement handlers immediately; reconcile Stripe subscription state against database; manually fix affected accounts |
| API not versioned, breaking CLI users | HIGH | Maintain the original unversioned endpoint indefinitely as the v1 equivalent; add `/v2/` with new schema; update CLI to detect API version |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Silent parse failures visible in SaaS | Pre-SaaS bug fix phase | Push a scan with a malformed .tf file; dashboard shows warning banner |
| Viewer code divergence | First SaaS phase (shared viewer package extraction) | Only one `DiagramCanvas` in codebase; CLI export and SaaS dashboard render identically |
| Scan artifact storage schema | Database schema design phase (before first push endpoint) | History page loads under 200ms for 50 scans; no blob loaded for list view |
| Window-injected data XSS risk in SaaS | SaaS viewer integration phase | CSP headers present; viewer reads from props, not window injection |
| Stripe webhook gaps | Billing integration phase | Simulated failed payment removes Pro access within 1 minute |
| CLI push API unversioned | CLI push command implementation phase | Endpoint is `/api/v1/scans`; `cli_version` field present in payload |
| Auth header not propagated Next.js to FastAPI | Auth infrastructure phase | Integration test confirms Next.js server component to FastAPI returns user-scoped data |
| CLI token stored insecurely | CLI auth implementation phase | `keyring` used; no token in any file readable via `cat` |
| Supabase public bucket | Infrastructure setup phase | Direct storage URL returns 403; signed URL required for access |
| Synchronous HCL parsing blocks API | Background task phase | `POST /scans` returns `scan_id` immediately; status polled separately |

---

## Sources

- Codebase analysis: `.planning/codebase/CONCERNS.md` — confirmed existing silent failure modes, security issues, performance bottlenecks (HIGH confidence)
- Project context: `.planning/PROJECT.md` — stack decisions, feature scope, constraints (HIGH confidence)
- CLI-to-SaaS transition patterns: Training knowledge on common failure modes including token storage, API versioning, webhook incompleteness (MEDIUM confidence — well-documented class of failures)
- IaC tooling domain specifics: Terraform plan JSON structure, HCL parsing edge cases, Supabase Storage + signed URL behavior (HIGH confidence)
- Supabase + FastAPI integration: Async client limitations, RLS gotchas, JWT verification with Supabase JWT secret (MEDIUM confidence — verify implementation details against Supabase docs)

---
*Pitfalls research for: IaC Visualization SaaS — CLI-to-SaaS transition*
*Researched: 2026-04-15*
