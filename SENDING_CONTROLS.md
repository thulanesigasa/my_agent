# Sending controls · Phase 6, first increment

Pull the update and restart both servers. Open **Settings → Sending controls**. No additional dependencies, credentials or paid services are required.

The pilot defaults to **five business-send attempts per connected mailbox per SAST day**, with business sending enabled subject to existing eligibility and explicit approval. Adjust the daily limit from 1 to 25 and click **Save daily limit**. This is an installation policy, not Gmail's quota or a claim about deliverability. It does not change provider billing settings or research budgets.

## Pause and usage

- Click **Pause business sending** to block new business submission reservations. The pause applies across backend processes using this SQLite ledger, persists after restarts and covers initial outreach, business replies and follow-ups.
- Already admitted/in-flight submissions may finish. Pausing cannot recall email already submitted. Use Gmail/history reconciliation for uncertain sends; do not assume a pause cancelled them.
- Draft preparation, research, inbox sync, owned-address connection tests, reports and internal admin notifications remain available. The switch controls this app's business sending, not email sent outside the app.
- Click **Reload controls & usage** to refresh the current mailbox's allowance. Settings shows the day and reset time in Africa/Johannesburg. Switching mailboxes changes the displayed usage; the pause and configured limit remain installation-wide, with separate per-mailbox daily counts.
- Resume with **Resume business sending**. Resuming or raising the daily limit never dispatches anything automatically. Existing pending/edited drafts still need approval. Changing the limit does not erase attempts already used. A stale editor receives a conflict instead of overwriting a newer pause or limit.

## What consumes an attempt

After connection, contact, reply and follow-up checks pass, a SQLite write transaction checks the current pause and allowance and reserves one slot immediately before provider submission. Separate processes cannot independently spend the same remaining slot. The reservation is linked to that dispatch record; repeating the same reservation is rejected.

A reserved slot remains consumed for the day even when the submission fails or delivery is uncertain. Explicit retries after known failures are new attempts and use another slot. The existing approval claim and uncertain-send reconciliation rules remain in force. A paused/capped attempt that was blocked before reservation does not consume a slot. Profile/eligibility failures before reservation also do not consume a slot.

The meter includes legacy confirmed, in-progress and uncertain business submissions recorded today before this policy was installed, so upgrading does not silently reset the day's activity. Historical failed records are not reconstructed as provider attempts. New submissions have a policy marker and are counted by their reservation rather than counted again as legacy records. This conservative attempt count can differ from Reports, which counts provider-confirmed submissions only.

The allowance resets by SAST calendar date at midnight, including across UTC date boundaries. No reset scheduler is needed. Pause remains active across midnight until explicitly resumed. The API enforces checks at approval and again immediately before sending, so pausing while provider preflight runs can still prevent a new reservation. A race rejected at this later check can leave an approval marked failed; after reviewing the reason, use the existing explicit retry controls when eligible.

## Scope and validation

Authenticated endpoints: `GET /api/sending-controls` returns current policy and mailbox usage; `PUT /api/sending-controls` changes the versioned pause/limit configuration. Policy changes and reservations are recorded in the activity ledger. Keep the SQLite database backed up and shared by the API/worker on the same host.

Offline tests cover concurrent reservations, daily boundaries, duplicate IDs, paused approvals, pause during preflight, quota exhaustion, uncertain submissions, legacy counts, mailbox separation, persistence, API authorization and stale edits. Fake provider responses are used; no real emails are sent during testing. Live Settings display/controls still need checking on your computer.

This is the operating-control foundation of Phase 6. It adds no campaign scheduler, automatic approval, automatic sending or paid fallback. Existing human review and contact-permission requirements remain. Research jobs retain their separate local attempt limits and pause/resume controls.
