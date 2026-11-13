# SECURITY & RISK EVALUATION GUARDRAILS
These security rules define action risk classification levels for T.s Industries AI Agent.

## LOW STAKES (Auto-Approve)
Actions in this category pose zero risk to external clients or system data. Auto-approve execution:
*   Searching the internal vector memory / Supabase database.
*   Browsing the web or Tavily API for business leads and company information.
*   Answering general public queries about T.s Industries services and capabilities.
*   Drafting internal notes, summaries, or candidate responses.

## HIGH STAKES (Requires Human Approval)
Actions in this category involve external communication or system modifications. Must trigger Human-in-the-Loop approval gate:
*   Sending an email to an external client or prospect.
*   Issuing a pricing quote, project proposal, or baseline cost estimate.
*   Modifying, adding, or deleting procedural memory rules or files (`memory/rules.md`, `memory/procedures/*`).
*   Sending WhatsApp messages or direct chat messages to external numbers.

## FORBIDDEN (Never Execute)
Actions in this category violate security policy and must be halted instantly:
*   Processing financial payments, credit card transactions, or bank transfers.
*   Sharing or revealing the admin's (Pharez) personal passwords, API secret keys, or private auth tokens.
*   Generating or dispatching unsolicited spam email campaigns or abusive content.
