# Operations after Phase 2

For local authorisation and the live test, follow [GMAIL_SETUP.md](GMAIL_SETUP.md).

## Startup checks

1. Start the API and dashboard using README instructions.
2. Check `/health` for process liveness and `/health/detailed` for local database and provider configuration status. “Configured” does not assert that remote credentials are valid.
3. Open the dashboard. A new installation has no leads, sends or approvals. API errors must appear as errors, not sample activity.
4. Enable a single scheduler owner only when ready to poll the configured mailbox. Weekly delivery is disabled until Phase 3.

## Restart verification

Approvals, leads, workflow tasks, submission records, activity events and local CRM/memory live in SQLite. Graph state lives in the adjacent checkpoints SQLite file. Restarting either process must not clear these files.

Use the dashboard Approval Queue and `GET /api/activity` to inspect outstanding records. Protected endpoints require the `X-API-Key` header when API protection is enabled.

The activity view shows **last recorded state**, not a live process heartbeat. A task or inbox record left `running`/`processing` after a crash remains held for review. No automatic recovery guesses whether external work happened. Conversation claims prevent two processes from running the same thread concurrently. Failed invocations release their thread claim; abrupt process termination can leave it held.

## Held dispatches

| State | Meaning | Action |
| --- | --- | --- |
| `pending` / `edited` | Draft awaits an explicit decision | Review and approve, edit or reject |
| `failed` | Gmail unavailable before submission | Fix configuration, then retry explicitly |
| `sending` | Send claimed; process may have been interrupted | Inspect Gmail Sent; do not resend automatically |
| `delivery_unknown` | Provider submission may have succeeded | Inspect Gmail Sent and reconcile before changing state |
| `sent` | Gmail returned a provider message ID | Do not resend this approval |
| `rejected` | Operator rejected the draft | No send allowed |

Do not reset an uncertain send to pending merely to clear the queue. Use Reconcile with Gmail Sent first. New submissions have a unique Message-ID persisted before the provider request. A positive matching provider record completes the original send; no unique match leaves it held. Legacy submissions without a correlation ID still need manual review with the API/worker stopped before database corrections. Back up first and retain the provider evidence. There is intentionally no one-click retry for uncertain submissions.

History sync atomically commits tracked incoming messages and its cursor, then processes the durable queue. Read/archived replies are included. Expired history IDs trigger a rescan of tracked threads. Failed optional drafting stays in the queue; retry it from Gmail settings. AI drafting defaults off. Unrelated threads are excluded. A mailbox sync lease prevents concurrent cursor updates and expires after five minutes after a crash.

## Backup and restore

Stop the API and worker before making a consistent backup of the entire data directory. Copy both SQLite files and any associated WAL/SHM files together, and store the copy somewhere private. On Docker, stop the services and back up the `agent_state` volume; do not remove that volume.

For restore, stop both processes, replace the complete data directory from the same backup, preserve file permissions, then restart. Reconcile held and recently sent work against Gmail before dispatching anything; restoring an old database does not unsend email and can lose local knowledge of a send.

Never back up only the old Postgres container and assume workflow data is covered. Hosted Supabase CRM/memory require their own backup procedure if configured.

## Provider failures

Missing Gmail and LLM providers are explicit errors. Configured Supabase failures do not switch to a new local CRM or memory store. Check server logs without sharing credentials. Supabase client construction and Gmail credential presence alone do not establish connectivity.

The Gmail webhook is disabled without a secret, rejects incorrect headers, rejects malformed payloads and returns 503 when processing cannot complete. Configure both Pub/Sub audience and service-account email for native Google OIDC verification, or use a trusted-relay shared secret. Polling needs no webhook.

## Scope

No live campaign, hosted database migration or deployment is required to validate the code. Operator authorisation and one controlled real test conversation are still required to validate the actual Gmail account. Run the offline suite and frontend build. Voice behaviour is outside this milestone. Contact eligibility is enforced in Phase 2; weekly reporting and autonomous campaigns remain later work.
