# Pilot readiness and read-only campaign previews

Pull the update and restart both servers. No new dependencies or credentials are needed. The implementation tests use isolated records/fake providers; they do not complete a real business pilot on your installation.

## Check recorded setup evidence

Open **Settings → Pilot readiness · local evidence** and click **Refresh local evidence**. The panel reads:

- Backend credential-loaded state and stored Gmail verification status for the current mailbox. These are cached facts, not a fresh OAuth/API test. Use **Verify or sync Gmail below** for a current connection check.
- Provider-confirmed connection-test submissions with correctly matched human replies. Acknowledgments such as “I got your email” are valid reply-cycle evidence even though their sales category is Needs review. Automated mail, bounces, unconfirmed submissions, wrong participants/threads and future-dated replies do not prove this cycle.
- Last successful sync timestamp, with a local 15-minute freshness check. This view does not sync or contact Gmail itself.
- In-progress/uncertain submissions requiring completion or reconciliation. Correlated approval/message records count as one submission rather than two.
- Current eligible lead count, sending pause/allowance, campaign drafting allowance and schedule configuration. Test contacts alone do not establish an eligible business lead.
- Optional research counters from this installation. Campaign previews/drafts do not use Tavily; these counters do not verify provider billing or account-wide credit use.

There is deliberately no overall “production ready” or “live pilot passed” score. Stored evidence does not prove current account access, inbox placement, website absence, activity or contact permission. The existing operator review and sending gates remain authoritative.

## Preview the next campaign batch

1. Complete the real evidence/permission review for the intended lead(s).
2. Open **Leads → Campaign schedules**, create a small paused campaign and select **Preview next batch · no changes**. A paused campaign can be inspected without activation.
3. Expand each member's preview. It shows the recipient, subject, body and project-selection rationale, or the current qualification/history/budget blocker. Existing approvals show their actual saved content and status; they are not replaced with newly generated wording.
4. Check the displayed run blockers, including paused/finished campaign state, an already-claimed batch today or an exhausted shared drafting budget. Sending pause/allowance is shown separately because it does not block draft preparation.
5. Refresh the preview after changing evidence, portfolio data or campaign progress. It makes no writes, reservations, approvals, run claims, provider requests or quota changes. It is advisory; a real batch checks current state again and may differ. Active schedules and other workers continue independently, so keep the campaign paused for stable inspection.

The preview covers the next configured batch from the saved cursor. It does not crawl pages, select additional businesses, alter contact permission or authorize sending. Historical business submissions and legacy approvals use the same duplicate checks as actual drafting. A record that would hit the campaign's daily drafting cap is marked budget-blocked; viewing it does not reserve a slot.

## Operator-reviewed live pilot

Start with one genuinely qualified, permitted business lead and a batch size of one. Verify Gmail and sync replies locally, inspect the paused campaign's dry run, then activate and explicitly prepare today's batch. Check its saved run history and exact Approval content before deciding whether to send. Keep the existing pilot daily sending limit small.

After a genuine response arrives, sync it, check the real participant/thread/body, review any suggested category and confirm the outcome with evidence. Refresh Reports for the original sent conversation's date range. Include connection tests only when validating your owned-mailbox test cycle; production reports exclude them by default. Saved report snapshots retain their original values.

Do not classify acknowledgments as Interested merely to complete the checklist. An actual sale requires operator evidence before marking Won. If a real response does not arrive, leave it awaiting reply; the seven-day follow-up workflow and its fresh-sync checks remain separate. There is no guaranteed reply rate or delivery result.

Record your actual findings from this live pilot, including any blocks or failures, before increasing activity. Your Windows/local UI, Gmail account and current business evidence cannot be fully tested from the implementation's offline fixtures. No real outreach is sent by readiness or dry-run checks.

Private read-only API routes: `GET /api/pilot/readiness` and `GET /api/campaigns/{id}/dry-run`. Existing API-key protection and campaign mailbox scoping apply. No preview is cached as a qualification, approval or pilot-completion certificate.
