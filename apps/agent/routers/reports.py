"""Authenticated reports, immutable exports and explicit conversation outcomes."""

from datetime import date
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from core.security import verify_api_key
from core.store import store
from services.email_service import email_service
from services.report_service import build_report, save_snapshot, workbook, queue_report

router = APIRouter(
    prefix="/api/reports", tags=["Reports"], dependencies=[Depends(verify_api_key)]
)


def mailbox():
    if not email_service.expected_email:
        raise HTTPException(400, "Configure and verify Gmail before using reports")
    return email_service.expected_email


def snapshot(report_id):
    report = store.get("reports", report_id)
    if not report or report.get("mailbox") != mailbox():
        raise HTTPException(404, "Report not found for this mailbox")
    return report


@router.get("/summary")
def summary(
    start: date | None = None, end: date | None = None, include_tests: bool = False
):
    try:
        return build_report(start, end, mailbox=mailbox(), include_tests=include_tests)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


class ReportInput(BaseModel):
    start: date | None = None
    end: date | None = None
    include_tests: bool = False


@router.post("/snapshots")
def create_snapshot(payload: ReportInput):
    try:
        return save_snapshot(
            payload.start,
            payload.end,
            mailbox=mailbox(),
            include_tests=payload.include_tests,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@router.get("/snapshots")
def list_snapshots():
    return {
        "reports": [
            {
                k: r.get(k)
                for k in ("id", "start", "end", "as_of", "summary", "include_tests")
            }
            for r in reversed(store.list("reports"))
            if r.get("mailbox") == mailbox()
        ]
    }


@router.get("/snapshots/{report_id}")
def get_snapshot(report_id: str):
    return snapshot(report_id)


@router.get("/snapshots/{report_id}/export")
def export_snapshot(report_id: str):
    report = snapshot(report_id)
    return Response(
        workbook(report),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename=outreach-{report['start']}-to-{report['end']}.xlsx"
        },
    )


@router.post("/snapshots/{report_id}/draft")
def draft_report(report_id: str):
    return queue_report(snapshot(report_id))


class OutcomeInput(BaseModel):
    outcome: Literal["unclassified", "interested", "declined", "won", "unsubscribed"]
    note: str = Field(min_length=1, max_length=2000)


@router.put("/conversations/{outbound_id}/outcome")
def set_outcome(outbound_id: str, payload: OutcomeInput):
    message = store.get("messages", outbound_id)
    if (
        not message
        or message.get("from") != mailbox()
        or message.get("status") != "sent"
        or message.get("purpose") not in ("outreach", "test")
        or not message.get("thread_id")
    ):
        raise HTTPException(404, "Confirmed conversation not found for this mailbox")
    if not payload.note.strip():
        raise HTTPException(400, "Record the evidence for this outcome")
    if payload.outcome in ("interested", "declined", "won"):
        human = [
            m
            for m in store.list("inbox")
            if m.get("mailbox") == mailbox()
            and m.get("thread_id") == message["thread_id"]
            and m.get("sender") == message.get("to")
            and not m.get("automated")
            and not m.get("bounce")
        ]
        if not human:
            raise HTTPException(
                400, "Sync a human reply before classifying its outcome"
            )
    return store.record_outcome(
        mailbox(),
        message["thread_id"],
        message["to"],
        payload.outcome,
        payload.note.strip(),
    )
