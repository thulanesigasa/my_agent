# Phase 3: real outreach reports

## Update on Windows

Keep the same repository directory, existing `.env`, credentials and runtime data. Stop the API/dashboard with Ctrl+C, then:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -r apps/agent/requirements.txt
npm --prefix apps/web ci
# Move the generated cache aside so the new styling configuration takes effect.
if (Test-Path apps/web/.next) { Move-Item apps/web/.next "$env:TEMP\my-agent-next-$([guid]::NewGuid())" }
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir apps/agent --host 127.0.0.1 --port 8000
```

In another terminal at the repository root:

```powershell
npm --prefix apps/web run dev
```

Open http://localhost:3000/dashboard and choose Reports. The PostCSS configuration now compiles the existing Tailwind styles, including the previously unstyled Gmail form. The sidebar and overall dashboard structure are retained.

## First report

1. Settings → Gmail → Sync replies. Reports read the ledger, not your entire mailbox, and do not initiate a sync themselves.
2. Reports → This week. Enable **Include connection tests** to see your Phase 2 test conversation; leave it off for real outreach statistics.
3. Refresh report. The default range is the previous complete Monday–Sunday week, so a new installation may correctly show zero.
4. For a synced human reply, select Interested, Declined or Won and record evidence. These are explicit operator classifications, not LLM guesses. Unclassified means no explicit outcome was recorded. **Unsubscribed also blocks sending to that contact.** Changing another outcome does not grant consent or undo suppression.
5. Save selected dates to keep a snapshot, or Export selected dates to Excel to save and download a new snapshot. Saved reports can be downloaded again and viewed without changing their original counts.
6. Create email draft on a saved report. The draft is addressed only to your connected Gmail mailbox, contains an Excel attachment from the saved snapshot, and appears in Approvals. Review the workbook and Approve & Send. Creating a draft or generating a scheduled report sends nothing. Repeated requests reuse the same approval, including its sent/rejected status.

The export contains Summary, Conversations, Daily and Definitions worksheets. User-controlled text is escaped against spreadsheet formula execution and invalid XML control characters are removed. Message bodies, OAuth tokens and API keys are not exported. Workbook files are generated from saved JSON snapshots; no paid storage is required.

## Metric definitions

| Figure | Meaning |
| --- | --- |
| Confirmed emails sent | Outreach submissions in the inclusive selected dates with a Gmail provider ID and confirmed sent state; tests only when explicitly included. |
| Conversations sent | Unique mailbox/thread conversations whose first recorded outreach/test submission is in the dates. Multiple sends in one thread do not inflate the denominator. |
| Conversations replied | Those conversations with at least one matched human reply by the snapshot time. Automated responses and bounces are excluded. |
| Reply rate | Conversations replied / conversations sent; blank if the denominator is zero. This is a conversation rate, not a message rate. |
| Awaiting reply | Cohort conversations with no human reply and no recorded bounce by the snapshot time; no age threshold is implied. |
| Bounced conversations | Cohort conversations with a recorded bounce. This can overlap replied if a conversation has both. |
| Human replies received | Human reply messages received during the selected dates, including replies to older tracked conversations. Multiple replies count as multiple messages here. |
| Outcomes | Latest explicit operator classification, or recorded opt-out. A recorded opt-out is not hidden by a later sales classification. |
| Daily activity | Submission counts and human reply messages per local calendar date. |

All date ranges are inclusive in Africa/Johannesburg. Reply dates use Gmail `internalDate`; legacy records missing it fall back to ingestion time and the report records a fallback count. Sends use the recorded submission-attempt time, including sends confirmed later through reconciliation. Pending, failed and delivery-unknown submissions do not count. Notifications and report emails do not count as outreach. Duplicate incoming provider IDs count once per mailbox. Records from a different connected mailbox are excluded from the report/export controls.

A refreshed report includes late replies up to its displayed **as-of** time. A saved snapshot remains unchanged, so a new snapshot of the same dates may show more replies. This avoids treating a still-unanswered recent message as a final failure. Last successful sync time is shown: stale or missing sync means the app may not yet know about a reply. Overview metrics use all recorded outreach conversations, while the Reports view uses its selected dates/mailbox.

Reports cover this installation's tracked conversations only; they do not import historical Gmail activity. Gmail acceptance is not proof of inbox placement, delivery or opening. There is no open tracking, invented sales outcome or automatic conversion attribution. Won is an operator-recorded outcome, not a verified payment record.

## Optional weekly generation

Add this to your existing root `.env` without replacing other settings:

```dotenv
WEEKLY_REPORTS_ENABLED=true
```

Run exactly one scheduler: either the worker below, or one API process with `ENABLE_SCHEDULER=true`, not both.

```powershell
.\.venv\Scripts\python.exe apps/agent/worker.py
```

Every Monday at 07:00 SAST it saves the previous complete Monday–Sunday week, excluding tests, and queues a report draft to your connected mailbox. It uses a deterministic mailbox/week key and atomic insert so repeated job execution does not duplicate the snapshot or approval. No LLM key or paid service is required. Scheduling is off by default. The machine/process must be running; if it was stopped at the scheduled time, use Reports to generate that period manually. Actual email delivery remains explicitly approved in this phase. Unattended dispatch is part of later controlled autonomy.

Keep the SQLite data directory backed up; it now also contains outcome history and report snapshots. There is no separate generated-file directory to back up. Very large exports are built in memory; this single-host design is intended for the small pilot, not unlimited multi-user scale.
