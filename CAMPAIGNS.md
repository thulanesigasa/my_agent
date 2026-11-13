# Campaign schedules · drafts for approval

Pull the update and restart both servers. No dependencies, provider keys or paid services have been added. Open **Leads → Campaign schedules · drafts for approval**.

1. Complete the business evidence review and record genuine contact permission for your leads. Only currently qualified/eligible leads appear in the selection list. Campaigns do not discover businesses, verify evidence, infer website absence, grant permission or send emails. Your connection-test contacts are not campaign leads.
2. Name the campaign, choose its daily SAST run time, select up to 20 eligible leads, and choose a batch size of 1–5 (default 3). Scheduled runs default to Monday–Friday; deselect that option for daily schedules. Membership and batch order are fixed at creation. To change the member list/schedule, cancel the remainder and create a new campaign.
3. Click **Save paused campaign**. Review its members and settings, then **Activate schedule**. At most five unfinished campaigns can be saved for the configured mailbox. Completed/cancelled campaigns remain in history and do not occupy an unfinished slot.
4. Keep the backend running at the scheduled time. Closing the dashboard does not pause a schedule. The local worker checks about every 30 seconds and queues a small batch of portfolio proposals for Approvals. It uses the same local composer as manual proposals, with no Gmail, Tavily, model or memory-provider request. Only the configured mailbox's campaigns run.
5. Optionally click **Prepare today's batch now** after activation. This explicit manual action can run before the scheduled time or on a weekend, but still consumes that campaign's one batch for the current SAST day. The next batch moves to the next permitted scheduled day; pausing/resuming does not unlock another batch today.
6. Read **Selected members and recent run history**. Each assessed lead is recorded as queued, existing approval or skipped, with the reason/status. A skipped or already-drafted lead still advances the fixed list and uses one drafting-attempt slot. Skipped leads are not automatically retried. Review/fix their evidence or permissions before deliberately selecting them for a new campaign.
7. Open **Approvals** to review/edit the saved messages and explicitly send. Newly created drafts show their campaign name. The existing contact, qualification, suppression, duplicate-send and business-sending controls are still enforced. No campaign action sends email automatically or approves a draft.

## Limits and pauses

Each campaign can claim at most one batch per SAST date, including failed/interrupted/manual batches. Across the installation, all campaigns share a fixed cap of **10 drafting attempts per SAST day**. Each step reserves a durable slot before composition; failures, skips, duplicates and interrupted steps keep their slot for the day. This is separate from the default five-per-mailbox business-send attempt limit. Raising a send limit does not raise the campaign drafting cap, and creating another campaign cannot bypass it.

A batch assesses at most its configured number of leads, not a guaranteed number of new drafts. When the shared draft budget is reached, the unassessed lead remains at the cursor for the next scheduled day. A campaign completes once the fixed list is exhausted. There are no automatic retries or additional leads fetched to fill a batch.

Use **Pause campaign** to stop subsequent steps. An already-started draft may finish saving, and existing approvals remain available. **Cancel remaining campaign** stops future steps permanently; it does not delete existing approvals. Business-send pause in Settings is separate: it blocks business submissions while campaign drafting/research can continue. Pause the campaigns too if you want draft preparation stopped.

The worker defaults to `CAMPAIGNS_ENABLED=true` and runs independently of the Gmail/report scheduler. With this flag false, scheduled ticks are disabled; activated campaigns can still run explicitly through the manual batch action. New installations contain no campaigns and creation always starts paused, so enabling the worker alone queues nothing.

## Restart and concurrency

Campaigns, cursors, daily run claims, slots and results are stored in the local SQLite ledger. A shared worker lease serializes campaign batches across API processes and manual/scheduled actions. Existing initial-outreach approval IDs remain unique per mailbox/contact; repeated campaigns cannot replace reviewed content or resend an initial message. Newly queued approvals retain campaign provenance, and run history links the exact approval used.

Active schedules survive restarts. An overdue schedule runs at most one batch for the current SAST date on a permitted weekday; missed dates are not replayed as separate batches. A graceful stop during an active batch pauses it for review. After a process crash, recovery waits for any abandoned lease to expire (up to about five minutes), marks the batch interrupted and pauses the campaign. Review Approvals as well as run history: a draft may have been saved just before cursor bookkeeping stopped. No already-saved draft is replaced on a later run.

Recovery does not reopen today's claimed batch. Resume permits the next scheduled day, preserving the cursor and daily limits. Global quota/batch claims are never reset by pause/resume/cancel. Keep the database backed up and the API/worker on the same host. A local schedule does not run while the computer/backend is off.

## API and validation

Private, API-key-protected routes: `GET/POST /api/campaigns`, `PATCH /api/campaigns/{id}` with action and configuration version, and `POST /api/campaigns/{id}/run`. Data/actions are scoped to the configured mailbox. Configuration accepts no automatic-sending switch. Stale controls return a conflict. The dashboard refreshes active campaign history about every 15 seconds; these local reads consume no provider credits.

Offline tests cover SAST/weekend schedules, paused creation, eligibility rechecks, single daily batches, shared quotas, fixed-list progress, duplicate approvals, in-flight pause, cancellation, worker exclusion/recovery, shutdown, persistence and API scoping. No real emails are sent for validation. The new UI and an eligible local pilot still need checking on your computer. This implements scheduled draft preparation; automatic sending, live lead discovery schedules and autonomous sales negotiation remain outside this increment.
