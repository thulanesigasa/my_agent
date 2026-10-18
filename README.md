# my_agent — T.s Industries outreach platform

A Python/FastAPI + LangGraph backend and Next.js dashboard for a local business website outreach workflow.

## Current milestone: Phase 6 bounded follow-up draft schedules

Phase 1 persists workflow records and approvals. Phase 2 adds a local OAuth connection helper, account verification, MIME message parsing, paginated history sync, reply threading, contact eligibility/suppression, uncertain-send reconciliation and connected Gmail dashboard controls.

**Start with [GMAIL_SETUP.md](GMAIL_SETUP.md)** for the exact Windows steps using your existing Google JSON. No credentials need to be uploaded. API and worker stay on one host; neither a paid host nor a public webhook is needed for polling.

Phase 3 adds real conversation reply metrics, inclusive SAST date ranges, operator-recorded outcomes, daily activity, saved snapshots, Excel exports and approval-controlled report attachments. See [REPORTING.md](REPORTING.md) for the reporting workflow and optional Monday schedule. The dashboard styling pipeline is restored.

Phase 4 adds free bounded OpenStreetMap discovery, manual/CSV candidates, source observations, identity/activity/website/contact review, duplicate checks and qualified-lead drafts. See [LEAD_RESEARCH.md](LEAD_RESEARCH.md). New business outreach starts in Leads. No new API key or LLM is required for the default research/manual draft flow.

Phase 5 now adds the supplied TS Industries portfolio, RBP Tech and Rhyma Music projects, editable project descriptions/industry tags, local template matching and editable proposal previews. See [PROPOSALS.md](PROPOSALS.md). Generating a proposal uses no Tavily/model credits, requires an eligible reviewed lead, and never sends automatically.

Phase 5 also provides local reply suggestions, editable response templates, explicit report-outcome confirmation and checks against answering an older synced message. See [REPLY_HANDLING.md](REPLY_HANDLING.md). Sync-time templates remain opt-in and approval-controlled. Incoming email text no longer enters the general command/LLM workflow through the inbox processor.

Controlled follow-up drafts are available in Outreach Logs: one after seven days with no recorded reply, current qualification/permission, a recent Gmail sync and explicit approval. See [FOLLOWUPS.md](FOLLOWUPS.md). An opt-in daily schedule can now prepare 1–3 eligible follow-up drafts for approval; it starts paused and never sends automatically.

Phase 6 now includes persistent business-send pause controls and atomic daily attempt limits in Settings. The default is five attempts per mailbox per SAST day, adjustable from 1 to 25. See [SENDING_CONTROLS.md](SENDING_CONTROLS.md).

Campaign schedules now prepare bounded portfolio proposals from explicitly selected eligible leads. New campaigns start paused; daily batches stop at fixed membership and shared drafting limits, and all messages remain in Approvals. See [CAMPAIGNS.md](CAMPAIGNS.md).

Read-only pilot evidence is available in Settings, with next-batch campaign previews in Leads. These checks show current recipients/content/blockers without changing quotas or queueing drafts. See [PILOT.md](PILOT.md) for the operator-reviewed live pilot.

Voice features are retained. Broader reply interpretation, scheduled live discovery and automatic sending remain later work.

## Roadmap

1. **Foundation:** persistence, truthful statuses, approval dispatch, webhook protection.
2. **Email integration (implemented; operator must authorise and run the live test):** full message parsing, Gmail history synchronisation, threading, delivery reconciliation, contact eligibility and suppression.
3. **Reporting (implemented):** actual reply outcomes, reporting periods, dashboard trends, Excel exports and attachments.
4. **Research and qualification (implemented):** supported sources, identity checks, website evidence and reviewed contact details.
5. **Outreach and conversation management (controlled workflow implemented):** portfolio matching, proposal/response templates, conservative reply suggestions, confirmed outcomes and a single approval-controlled no-response follow-up are available. Broader interpretation remains an improvement area.
6. **Controlled autonomy (in progress):** business-send pause/daily limits, approval-only campaign schedules, read-only pilot checks and opt-in bounded follow-up draft schedules are implemented; broader automation, additional spending controls and operator validation of a live pilot remain.

Reports use only provider-confirmed submissions and matched incoming records from this installation. Tests are excluded by default. Reply rates count unique conversations and are blank when no conversations were sent. Interested/declined/won outcomes require an operator note and a synced human response. Unsubscribe blocks further contact. Gmail acceptance does not prove inbox delivery or opening. Scheduled reports are opt-in and queue a draft for approval; they never send themselves.

## Run locally

Python 3.11+ and Node.js 22 are recommended. From the repository root:

```powershell
# First-time setup only: keep your existing .env if you already have one.
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r apps/agent/requirements.txt
.venv\Scripts\python.exe -m uvicorn main:app --app-dir apps/agent --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
npm --prefix apps/web ci
npm --prefix apps/web run dev
```

Open `http://localhost:3000/dashboard`. On Linux/macOS use `cp .env.example .env` and `.venv/bin/python` in place of the Windows commands.

The dashboard can show an empty database without any paid account. Chat/drafting needs a configured supported model provider. Sending needs the locally authorised token file; legacy OAuth environment values are also supported when bound to `GMAIL_USER_EMAIL`. The Gmail test cycle does not need an LLM key. Missing providers return explicit errors. Configure supported model names for the provider you choose; availability depends on that account.

The scheduler is off by default. To run polling, either start `.venv\Scripts\python.exe apps/agent/worker.py` in a separate terminal **or** set `ENABLE_SCHEDULER=true` for a single API process. Do not enable both. The worker uses the existing South African active-hours calendar. Starting a worker does not launch an autonomous outreach campaign.

## Data and configuration

- Native runs: `apps/agent/data/agent.sqlite3` plus `agent.sqlite3.checkpoints.sqlite3`.
- Override with an absolute `STATE_DB_PATH` when needed. Both processes must resolve the same file on the same host.
- With no Supabase URL/key, CRM and memory use durable local SQLite. If both Supabase values are configured, those services use Supabase and surface errors instead of silently falling back. Existing Supabase records are not copied into local storage, or vice versa.
- Workflow records and checkpoints remain local even when Supabase memory/CRM are enabled. These phases do not deploy or modify a hosted Supabase project.
- Production configuration requires `API_KEY_REQUIRED=true` and a non-default `AGENT_API_KEY`. This check does not replace a full public-hosting authentication design.
- Frontend settings are read from Next.js environment configuration. The default local dashboard needs no API key; protected environments need an appropriate private operator access setup. Do not publish an operator API key in a public web bundle.
- `WEBHOOK_SECRET` enables the shared-secret Gmail webhook. Only an exact `X-Goog-PubSub-Token` header is accepted; query-string credentials and substring matches are rejected. This endpoint expects a trusted relay that injects the secret. Native OIDC verification is available when both Pub/Sub settings are configured; polling and push share the same durable history cursor.
- Never commit `.env`, databases, client records or runtime backups.

## Docker

Copy `.env.example` to `.env` first, then:

```bash
docker compose up --build -d
```

API and worker mount the same `agent_state` volume at `/app/data`. The API scheduler is explicitly disabled; the worker owns scheduling. The agent image uses `CMD` so the worker command actually overrides the API command. `docker compose down` preserves the volume; `docker compose down -v` deletes it.

The legacy Postgres container is not the workflow ledger and is not a complete local Supabase installation. Optional hosted Supabase access still uses the configured URL/key.

## Approval behaviour

- Drafts are saved before they appear in the queue. There are no seeded approvals.
- **Edit Draft → Save Draft** updates the persisted draft without sending.
- **Approve & Send** dispatches the reviewed database record; duplicate clicks cannot dispatch it twice.
- **Reject** prevents sending that approval.
- Missing Gmail configuration leaves a visible `failed` record that can be retried once configured.
- An uncertain provider exception, interrupted dispatch or missing provider message ID leaves `delivery_unknown` or `sending`. These states block resending; use the provider-evidence reconciliation control. Unresolved submissions stay held.
- An approved initial email does not automatically move a business to “In Progress” or claim a project has been won.

See [RUNBOOK.md](RUNBOOK.md) for restart, backup and held-work guidance.

## Verify without external services

```bash
python -m pip install pytest pytest-asyncio
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=apps/agent python -m pytest -p pytest_asyncio.plugin apps/agent/tests -q
npm --prefix apps/web run typecheck
npm --prefix apps/web run build
```

PowerShell: set `$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD="1"` and `$env:PYTHONPATH="apps/agent"`, then run `python -m pytest -p pytest_asyncio.plugin apps/agent/tests -q`.

Tests use temporary databases and explicit fake providers, clear provider/tracing credentials, disable LangSmith's pytest integration, and block external socket connections. CI runs Python formatting/lint on changed files, the backend suite and the frontend typecheck/build. Unrelated legacy voice modules are not reformatted as part of this milestone.

## Licence

Copyright © 2026 T.s Industries. All rights reserved. See [LICENSE](LICENSE).
