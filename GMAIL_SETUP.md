# Phase 2: connect and test Gmail on Windows

Run these steps on the computer that will run my_agent. Keep your downloaded Google JSON and token files on that computer. Do not upload them to chat or commit them to GitHub.

## 1. Update the code and dependencies

Open PowerShell in your repository and activate your existing Python environment, then:

```powershell
git pull origin main
python -m pip install -r apps/agent/requirements.txt
```

Use the same Python environment for installation, the connection helper, and the backend. Node dependencies did not change in this phase.

## 2. Put your existing JSON in the ignored folder

```powershell
New-Item -ItemType Directory -Force .secrets
Copy-Item "C:\Users\YOUR_NAME\Downloads\YOUR_DOWNLOADED_FILE.json" ".secrets\gmail-client.json"
```

Replace the source path with your actual downloaded file. Do not replace text inside the JSON. The `.secrets` folder is excluded from Git and the Docker build context.

Open the JSON locally only to determine its client type:

| Top-level section | What it means | Action |
| --- | --- | --- |
| `installed` | OAuth Desktop client | Supported directly |
| `web` | OAuth Web client | Supported with the loopback redirect below |
| `type: service_account` | Service-account credentials | Use an OAuth Desktop client for this personal Gmail connection |

For a Web client, register **`http://localhost:8765/`** under its authorised redirect URIs in Google Cloud Console. Download the updated JSON and copy it into `.secrets/gmail-client.json` again. Alternatively create a Desktop OAuth client in the same existing project. You do not need to create a new Cloud project just because the client type differs.

Your existing Google project must have **Gmail API enabled**. For an External OAuth app in Testing mode, add your sending Gmail account as a test user under Google Auth platform → Audience. See Google's [consent setup](https://developers.google.com/workspace/guides/configure-oauth-consent) and [Python Gmail quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python).

## 3. Authorise the intended sending account

```powershell
python connect_gmail.py authorize --account YOUR_SENDING_ADDRESS@gmail.com
```

Replace the address with your actual primary Gmail address. The helper opens Google's sign-in page, requests offline access, and asks for permission to read messages and send mail. Select the intended account and approve both permissions. Only approve the application if it is your own configured Google client.

The helper checks the account returned by Gmail before saving anything. A wrong account or incomplete permission grant does not save a new token. If authorisation is cancelled or times out, rerun the command when ready.

The resulting `.secrets/gmail-token.json` contains the credentials the application needs. No secret is printed to the terminal. You do not need to copy the token into chat or manually copy a refresh token into `.env`.

If you already have `GMAIL_USER_EMAIL` in `.env`, set it to the same address, or leave it blank to use the account bound to the new token. A stale different value causes an account-mismatch error. The token file takes precedence over legacy client-ID/client-secret/refresh-token environment settings.

## 4. Check the connection without sending

```powershell
python connect_gmail.py check
```

Expected output includes:

```text
Verified Gmail account: your-address@gmail.com. No email was sent.
```

Restart the API and worker so both load the new token. Start the frontend as usual. Open **Dashboard → Settings → Gmail connection → Verify connection**. This performs another provider check; it does not send a message.

## 5. Record an address you control for the test

Use a **second, different mailbox** you control. Sending to the same primary account does not provide a meaningful external reply test, and the application rejects that test draft.

In Dashboard → Settings → Contact eligibility:

1. Enter the second mailbox address.
2. Record evidence such as “This is my second email account; I control this inbox.”
3. Tick **I control this address and will use it for connection tests**.
4. Leave marketing permission as **Not recorded** if it is only a connection test.
5. Save the contact.

Test-address ownership does not grant permission to send marketing. Business outreach separately requires verified contact details and recorded consent with evidence. Declined and unsubscribed contacts are blocked even for test sends.

## 6. Send one reviewed test message

In Create a draft:

1. Select **Connection test to an address I control**.
2. Enter the second address.
3. Review the subject and body.
4. Click **Save for approval**. Nothing is sent yet.
5. Open **Approval Queue**, review the saved draft, then click **Approve & Send**.

Confirm it appears in the sender's Gmail Sent folder and arrives in your second mailbox. Gmail accepting the submission is not proof of recipient delivery or opening; checking both inboxes validates this controlled test.

## 7. Reply and sync

1. From the second mailbox, reply to the test email using the normal Reply button.
2. Back in Dashboard → Settings, click **Sync replies**.
3. Confirm the message appears under **Replies in recorded conversations**.
4. Click **Reply** on that incoming message, write your response in Create a draft, save it, then approve it.
5. Confirm the response remains in the same Gmail conversation.

The recipient, original Message-ID and Gmail thread are taken from the saved incoming record. Read or archived replies are included; the application does not rely on unread status. Repeating sync must not duplicate the incoming record. Incoming messages from unrelated conversations are not imported into the agent queue.

Local reply-template drafting is **off by default** (`GMAIL_DRAFT_REPLIES=false`). Reply suggestions and manually requested templates use no model or research credits. If enabled, sync queues templates only for eligible, current human messages with a clear interest/question signal. Mixed/uncertain messages, declines, opt-outs, automated mail and bounces do not get automatic templates. Incoming text is not passed to the general command/LLM workflow. Templates still require review and explicit sending approval. See [REPLY_HANDLING.md](REPLY_HANDLING.md).

## 8. Restart and failure checks

Restart the application, verify the mailbox, and sync again. Existing messages and approvals should remain.

If an email submission times out, the application holds the approval as `sending` or `delivery_unknown`. Use **Reconcile with Gmail Sent** in the Approval Queue. It searches for the unique Message-ID stored before the original submission and checks the returned account, recipient, subject and Sent label. It never sends another email. No match or ambiguous evidence keeps the submission held. Legacy Phase 1 submissions without correlation IDs require manual provider review.

If optional reply drafting fails, the actual reply remains recorded. **Retry processing** retries that saved incoming message, not the outgoing send. Consent withdrawals are applied when the mailbox data is committed, before any AI step.

## Troubleshooting

| Message or symptom | What to check |
| --- | --- |
| Credentials file not found | Confirm `.secrets/gmail-client.json` exists and run from the repository root |
| API key or service-account JSON rejected | Download an OAuth Desktop client JSON from the existing Google project |
| Wrong Google account selected | Rerun `authorize --account ...` and choose the matching primary account |
| Missing permissions/offline access | Rerun authorisation and approve both Gmail permissions |
| `redirect_uri_mismatch` with a Web client | Register exactly `http://localhost:8765/`, including the slash, then download the updated JSON |
| Access blocked for a test user | Add the sending address under Google Auth platform → Audience → Test users; Workspace policies can also restrict access |
| Gmail access refused | Check Gmail API enablement, granted permissions and account/organisation policy |
| Reauthorisation required | Rerun the helper, then restart API and worker |
| No reply appears | Verify it was a reply to an app-recorded send, from the expected second address, then sync; a new independent email is not a tracked reply |
| Mailbox sync busy | Let the current sync finish and retry; a crashed sync lease expires after five minutes |
| Contact ineligible | Record ownership for a controlled test, or actual verification and consent evidence for outreach |

An External OAuth app in **Testing** generally receives refresh tokens that expire after **seven days** when Gmail scopes are requested. Revocation and certain account changes can also invalidate tokens. Reauthorise as needed for the pilot. Sustained/public operation requires assessing the app's publishing and verification requirements; clicking Publish does not itself mean Google verified it. See [Google's refresh-token documentation](https://developers.google.com/identity/protocols/oauth2#expiration) and [Gmail scope requirements](https://developers.google.com/workspace/gmail/api/auth/scopes).

## Polling, optional push and Docker

Use manual Sync first. For scheduled sync, run one worker or enable scheduling in one API process, not both. No Google Pub/Sub setup or public callback is needed for this local polling pilot.

Optional native push supports `PUBSUB_AUDIENCE` and `PUBSUB_SERVICE_ACCOUNT_EMAIL`: both must be set, and the endpoint verifies the Google ID token's signature, audience, issuer, expiry, verified email and expected service-account identity. Provisioning subscriptions and Gmail watch renewal is an operator deployment task; it is not automatically created by this phase. An existing trusted relay can instead use `WEBHOOK_SECRET` when OIDC settings are absent.

On Docker, run the authorisation helper on the host first. Compose mounts `./.secrets` read-only at `/app/secrets` in both API and worker and sets `GMAIL_TOKEN_PATH=/app/secrets/gmail-token.json`. The token is not copied into an image. Default published ports are bound to localhost. Custom frontend origins must be explicitly added to `CORS_ORIGINS` rather than using wildcard access.

Back up the workflow data directory and protect the separate credentials folder. Restore with the API/worker stopped and reconcile sends against Gmail before resuming. This phase does not activate a business outreach campaign or complete Google's public-app verification on your behalf.


## Test email landed in spam

A successful API submission proves Gmail accepted the message, not inbox placement. Phase 3 uses standard SMTP CRLF serialization, retains a unique Message-ID, Date and actual verified From address, and preserves real reply headers. It does not forge SPF/DKIM results or claim to fix spam filtering.

For a useful comparison, send one ordinary message manually from Gmail to the same test mailbox. In the received app message, inspect the provider's **Show original / View message source** screen and its Authentication-Results (SPF, DKIM and DMARC) plus any spam reason. Record whether the manual message also landed in spam. Share only redacted authentication results and the stated spam reason if you want help interpreting them; the full source may expose addresses and message content. For an @gmail.com sender, Google manages the domain's authentication; there is no gmail.com DNS record for you to edit.

Use a clear sender identity and subject, real portfolio links, relevant permission-based content, and honour opt-outs. Do not add fake authentication headers, misleading Re: prefixes, tracking pixels or repeated test blasts as a purported fix. Gmail filters are recipient/provider dependent; passing authentication is not an inbox guarantee. See [Google's sender guidelines](https://support.google.com/mail/answer/81126?hl=en).

Once a test reply syncs, open Reports, select This week and Include connection tests, then refresh. Your test can now appear in a report without inflating outreach-only statistics. See [REPORTING.md](REPORTING.md).
