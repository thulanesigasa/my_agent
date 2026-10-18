"""Read-only pilot evidence and campaign batch previews. No provider calls or writes."""

from datetime import datetime, timezone

from config import settings
from core.store import store, now
from services import campaigns, send_controls
from services.email_service import email_service
from services.lead_service import ensure_qualified, initial_outreach_state
from services.proposals import compose_qualified_proposal
from services.report_service import instant, incoming_time
from services.web_research import research_status


def dry_run(campaign_id, mailbox):
    campaign = store.get("campaigns", campaign_id)
    if not campaign or campaign["mailbox"] != mailbox:
        raise KeyError(campaign_id)
    budget = campaigns.usage()
    rows = []
    remaining = campaign["lead_ids"][
        campaign["cursor"] : campaign["cursor"] + campaign["batch_size"]
    ]
    for index, lead_id in enumerate(remaining):
        candidate = store.get("leads", lead_id) or {}
        row = {
            "lead_id": lead_id,
            "name": candidate.get("name", "Missing lead"),
            "recipient": "",
            "decision": "blocked",
            "reason": "",
            "subject": "",
            "body": "",
            "projects": [],
        }
        try:
            lead = ensure_qualified(lead_id)
            _, existing = initial_outreach_state(lead, mailbox)
            row["recipient"] = lead["review"]["email"]
            row["name"] = lead["review"].get("confirmed_name") or lead["name"]
            if existing:
                row.update(
                    decision="existing_approval",
                    reason=f"Existing approval is {existing['status']}; it will not be replaced",
                    subject=existing["subject"],
                    body=existing["draft_response"],
                    projects=(existing.get("proposal_snapshot") or {}).get(
                        "projects", []
                    ),
                )
            else:
                proposal = compose_qualified_proposal(lead, mailbox)
                row.update(
                    decision="would_queue",
                    reason="Eligible for a new approval draft at the time of this preview",
                    subject=proposal["subject"],
                    body=proposal["body"],
                    projects=proposal["projects"],
                )
        except (ValueError, KeyError) as exc:
            row["reason"] = (
                str(exc)
                if not isinstance(exc, KeyError)
                else "The saved lead no longer exists"
            )
        if index >= budget["remaining"]:
            row.update(
                decision="budget_blocked",
                reason="The shared daily campaign drafting budget would stop before this lead",
            )
        rows.append(row)
    blockers = []
    if campaign["status"] != "active":
        blockers.append(
            f"Campaign is {campaign['status']}; previewing does not activate it"
        )
    if store.get("campaign_runs", f"{campaign_id}:{budget['day']}"):
        blockers.append("This campaign already claimed its batch for today")
    if not remaining:
        blockers.append("No unassessed members remain")
    if budget["remaining"] <= 0:
        blockers.append("The shared daily campaign drafting budget is exhausted")
    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign["name"],
        "campaign_status": campaign["status"],
        "cursor": campaign["cursor"],
        "generated_at": now(),
        "rows": rows,
        "run_blockers": blockers,
        "draft_budget": budget,
        "sending": send_controls.status(mailbox),
        "worker_enabled": settings.CAMPAIGNS_ENABLED,
        "read_only": True,
        "warning": "This is a local preview, not a reservation or approval. A real batch rechecks current data and can produce different results. Active schedules continue independently; pause the campaign for a stable inspection.",
    }


def readiness(mailbox, *, at=None):
    at = at or datetime.now(timezone.utc)
    connection = store.get("gmail_connection", "current") or {}
    cursor = store.get("gmail_cursor", mailbox or "") or {}
    synced = instant(cursor.get("updated_at"))
    fresh_sync = bool(synced and 0 <= (at - synced).total_seconds() <= 900)
    messages = [
        m for m in store.list("messages") if mailbox and m.get("from") == mailbox
    ]
    incoming = [
        m for m in store.list("inbox") if mailbox and m.get("mailbox") == mailbox
    ]
    completed_tests = []
    for message in messages:
        sent = instant(message.get("created_at"))
        if (
            message.get("purpose") != "test"
            or message.get("status") != "sent"
            or not message.get("provider_message_id")
            or not sent
            or sent > at
        ):
            continue
        replies = [
            m
            for m in incoming
            if m.get("matched_outbound_id") == message["id"]
            and m.get("sender") == message.get("to")
            and m.get("thread_id") == message.get("thread_id")
            and not m.get("automated")
            and not m.get("bounce")
            and (received := incoming_time(m))
            and sent <= received <= at
        ]
        if replies:
            completed_tests.append(message["id"])
    held = {
        m["id"] for m in messages if m.get("status") in ("sending", "delivery_unknown")
    }
    held.update(
        a.get("dispatch_id") or f"approval:{a['id']}"
        for a in store.list("approvals")
        if a.get("sender_mailbox") == mailbox
        and a.get("status") in ("sending", "delivery_unknown")
    )
    eligible = 0
    for lead in store.list("leads"):
        try:
            ensure_qualified(lead["id"])
            eligible += 1
        except (ValueError, KeyError):
            pass
    policy = send_controls.status(mailbox, at=at)
    budget = campaigns.usage(at)
    jobs = [c for c in store.list("campaigns") if c["mailbox"] == mailbox]
    verified = bool(
        mailbox
        and connection.get("status") == "verified"
        and connection.get("email") == mailbox
    )
    checks = [
        {
            "name": "Gmail configuration",
            "status": "pass" if email_service.is_configured and mailbox else "action",
            "detail": (
                "Credentials were loaded by the backend"
                if email_service.is_configured and mailbox
                else "Configure Gmail locally and verify the account in Settings"
            ),
        },
        {
            "name": "Recorded account verification",
            "status": "pass" if verified else "action",
            "detail": f"Stored status: {connection.get('status', 'not verified')}. Last recorded update: {connection.get('updated_at', 'not available')}. Verify connection for a current check.",
        },
        {
            "name": "Owned-mailbox send and reply evidence",
            "status": "pass" if completed_tests else "action",
            "detail": f"{len(completed_tests)} provider-confirmed test conversation(s) with a matched human reply recorded locally",
        },
        {
            "name": "Recent reply sync",
            "status": "pass" if fresh_sync else "action",
            "detail": f"Last recorded sync: {cursor.get('updated_at', 'not available')}. Sync before a live pilot; this view does not contact Gmail.",
        },
        {
            "name": "Submission reconciliation",
            "status": "pass" if not held else "action",
            "detail": f"{len(held)} submission(s) in progress or uncertain. Let active submissions finish; review held ones in Approvals and Gmail Sent.",
        },
        {
            "name": "Eligible business leads",
            "status": "pass" if eligible else "action",
            "detail": f"{eligible} lead(s) currently pass evidence and contact-permission checks. Test contacts alone do not qualify business leads.",
        },
        {
            "name": "Business sending controls",
            "status": (
                "action"
                if policy["config"]["paused"] or not policy["remaining"]
                else "pass"
            ),
            "detail": f"Sending {'paused' if policy['config']['paused'] else 'enabled'}; {policy['remaining']} of {policy['config']['daily_limit']} attempt slots remain for this mailbox today.",
        },
        {
            "name": "Campaign drafting budget",
            "status": "pass" if budget["remaining"] else "action",
            "detail": f"{budget['remaining']} of {budget['limit']} drafting attempts remain across the installation today.",
        },
        {
            "name": "Campaign schedules",
            "status": "info",
            "detail": f"{sum(c['status'] == 'active' for c in jobs)} active; {sum(c['status'] == 'paused' for c in jobs)} paused. Scheduled worker configuration: {'enabled' if settings.CAMPAIGNS_ENABLED else 'disabled'}. Preview the chosen campaign before activation.",
        },
    ]
    return {
        "generated_at": at.isoformat(),
        "mailbox": mailbox or "",
        "checks": checks,
        "research": research_status(),
        "read_only": True,
        "warning": "Local evidence only. This does not test current credentials, prove deliverability, certify business facts or authorize sending. Complete a small operator-reviewed live pilot separately.",
    }
