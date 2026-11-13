# Town targeting, OpenAI and ElevenLabs

This update adds a working provider integration, not provisioned accounts or a verified telephone service. It makes no live calls during installation or tests. Keep your current Gmail OAuth files, SQLite data and approval flow. Do not paste keys into chat or commit `.env`.

## 1. Pull and restart

From your Windows repository, stop the two servers and run:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -r apps/agent/requirements.txt
npm --prefix apps/web ci
```

No new mandatory package is introduced. Restart with your existing commands:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir apps/agent --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
npm --prefix apps/web run dev
```

## 2. Select one town for the month

Open `/dashboard` → Settings → Automation. Enter the month, town, region (optional), country, industry and an IANA time zone, such as `Africa/Johannesburg` or `Europe/London`. Save paused first. The saved-month selector recalls the latest target for that month; it does not automatically activate a future month's target. Select a saved profile and save to use it. Monthly profiles are scoped to the connected Gmail mailbox.

The exact town/region/country label scopes new initial drafts. Tavily searches that label; it is a research constraint, not proof that every returned result is physically in town. Review actual source/branch details. Worldwide town names are accepted, including non-Latin text; source availability, automatic qualification and contact interpretation do not become universally supported merely because a country was selected. Existing strict supported-source qualification remains in place. Nonmatching/unsupported candidates remain for review.

The research/initial/follow-up automation window uses the saved time zone and selected month. Reply processing, Gmail sync and reports can continue outside that window for existing conversations. Existing independent schedules and manual controls retain their own settings; leave unused legacy schedules paused. Daily drafting/research accounting still uses the existing SAST calendar, while paid reservations use UTC months. Saving a changed target pauses old active automatic research jobs; an already started HTTP request may finish. An already claimed daily research job is not replayed for a new town on the same SAST day.

Use your existing Tavily configuration:

```dotenv
ALLOW_TAVILY_RESEARCH=true
TAVILY_API_KEY=your_local_key
TAVILY_DAILY_QUERY_LIMIT=5
TAVILY_MONTHLY_QUERY_LIMIT=100
```

Search and extraction share those existing limits. No Google Maps scraping/import or new paid research subscription is introduced.

## 3. Configure OpenAI and the blob's voice

In your root backend `.env`, set:

```dotenv
LLM_PROVIDER=openai
OPENAI_API_KEY=your_local_api_key
OPENAI_MODEL=gpt-4.1-mini
VOICE_PROVIDER=elevenlabs
ELEVENLABS_API_KEY=your_local_elevenlabs_key
ELEVENLABS_VOICE_ID=the_voice_id_from_your_account
ELEVENLABS_TTS_MODEL=eleven_flash_v2_5
```

Choose a voice/model available under your account's current plan. These are backend settings; none should use a `NEXT_PUBLIC_` prefix. If the backend requires an operator API key, set `AGENT_API_URL` and `AGENT_API_KEY` in the frontend’s local `apps/web/.env.local`; Next.js does not automatically read the repository root `.env`. Follow the existing private dashboard connection configuration as well. This feature does not grant a hosted Next.js site user authentication: keep the operator site private and do not expose an authenticated proxy publicly without access control.

Restart both servers. On `/`, click the blob or **Voice conversation**, allow the microphone and speak. In supported browsers the microphone recognition uses the browser, the existing agent uses the selected OpenAI model, and the answer is read using ElevenLabs. Browser speech recognition may itself use a remote browser service. A configured paid provider failure is shown; it never silently switches to another paid model or a different voice. Replies longer than 3,000 characters remain fully visible as text but only their first 3,000 characters are spoken.

To use ElevenLabs transcription too, set:

```dotenv
STT_PROVIDER=elevenlabs
ELEVENLABS_STT_MODEL=scribe_v2
```

That chooses the existing server audio/WebSocket pipeline on the voice button. Both recognition and voice output can then consume ElevenLabs allowance. Browser wake standby is disabled in that mode; use the blob/voice button or desktop double-clap launch. For browser wake listening with ElevenLabs output, leave `STT_PROVIDER=groq` (it is not called by browsers with native recognition), enable wake listening and say **elevate agent**. Double claps and optional Vosk desktop wake recognition are retained; see `VOICE_CHAT.md`.

Text and server/browser voice use the same conversation ID. Up to 100 displayed turns per conversation are saved in the existing local SQLite ledger and the last 12 turns (bounded by characters) are passed to drafting as context. The browser stores only the thread IDs, not message bodies or provider keys. Reloading the same browser restores its conversation from that backend. New conversation starts another ID; it does not erase older server records or LangGraph checkpoints. This is conversation recall, not model training or unlimited semantic memory. Protect and back up the database. Call transcripts have their own business-scoped records and cannot become owner instructions.

## 4. Budget controls before paid use

The default local ceiling is £40 per UTC month. £15 is reserved for subscriptions/other costs, leaving £25 for conservative request reservations. Defaults reserve 10p per selected OpenAI model request, 10p per ElevenLabs speech request and £1 per outbound call attempt; model turns during a phone call also reserve 10p each. These figures are configurable estimates, not provider prices or invoice measurements. Failed and uncertain requests retain their reservation. No automatic provider retries are enabled in the selected model client.

Set the fixed reserve to your actual subscription/number costs and choose sufficiently conservative per-request amounts. Keep taxes and currency movement in mind. Set provider-side spending/usage caps and disable overages where available. Usage outside this installation, provider subscriptions, inaccurate estimates, exchange rates, carrier charges or multiple installations can exceed local estimates. The application cannot promise an absolute £40 vendor bill. Settings shows remaining local allowance, not account balances. Existing Tavily credit limits are separate.

## 5. Telephone setup without Twilio

An ordinary cellphone/SIM number is not automatically a SIP line. Ask your carrier whether it supports an authorized outbound SIP trunk or another supported arrangement for that number. Owning it or forwarding incoming calls alone does not enable outbound API dialing. We have not purchased, ported or connected a number for you.

Create a dedicated ElevenLabs phone agent and import a SIP-connected number using the official [SIP guide](https://elevenlabs.io/docs/eleven-agents/phone-numbers/sip-trunking). Phone IDs are ElevenLabs resource IDs, not `+27...` strings.

For shared code/memory, configure the agent to use **Custom LLM**:

- Endpoint: `https://your-private-proxy.example/api/calls/llm/v1/chat/completions`
- API key/Bearer secret: a dedicated random secret of at least 32 characters; use the same value as `ELEVENLABS_LLM_SECRET` below. Never use the owner API key or OpenAI key for this bridge.
- Enable the `end_call` system tool; do not add email, admin, MCP, server tools or agent workflows. The app rejects imported external tool IDs and other tool definitions.
- Permit first-message and conversation-duration overrides. The app supplies the AI disclosure and a maximum duration, default three minutes. An override rejected by ElevenLabs is held conservatively; it is not retried.
- Expose only this bridge route via HTTPS to ElevenLabs. Keep the dashboard and all operator APIs private. The bridge rejects missing secrets even when local operator authentication is disabled.

Set these backend values, then restart:

```dotenv
ELEVENLABS_AGENT_ID=your_dedicated_agent_id
ELEVENLABS_PHONE_NUMBER_ID=your_imported_sip_phone_id
ELEVENLABS_LLM_URL=https://your-private-proxy.example/api/calls/llm/v1/chat/completions
ELEVENLABS_LLM_SECRET=your_dedicated_random_secret
ELEVENLABS_CALLS_ENABLED=false
CALL_MAX_SECONDS=180
```

Verify the provider configuration and permitted destination/rates before setting `ELEVENLABS_CALLS_ENABLED=true`. Merely creating an ElevenLabs account or supplying its key is insufficient. No service is deployed or phone account reconfigured by this code.

## 6. Review the first call

Settings → Voice and phone calls shows configuration blockers. Select a qualified business in the saved town and record actual permission for an AI call, independently of its existing email permission. A published number is not consent. Country-specific marketing/recording rules and do-not-call requirements must be checked for the destination before approval; this pilot does not check external national registries. Begin with a permitted test business/number you control or a requested callback.

Prepare a call, review the exact number, opening, permission evidence and duration, then choose **Approve and call this number**. Preparation never dials. Calls are limited to weekdays 09:00–17:00 in the selected time zone/month, one saved proposal per business/number/month, and one active or uncertain submission globally. Dispatch rechecks qualification, source fingerprint, target fingerprint, suppression and allowance. Changing evidence blocks the saved proposal rather than silently rewriting it.

ElevenLabs receives only the call binding and approved opening/duration. Its Custom LLM requests are bound to that call with a temporary per-call token, use our OpenAI key server-side, and receive only that business's selected facts and recent saved call context. They never enter the owner command graph. At most 12 distinct paid turns are allowed; identical completed turns return the saved response. Speech is returned in OpenAI-compatible SSE. Live latency/turn-taking still requires a real provider test.

Choose **Sync call result** to fetch provider status, transcript and summary into the local ledger. This is explicit polling, not automatic webhook ingestion. Provider summaries are unverified business data. Future call context can recall completed conversations with that same business; it does not read unrelated owner conversations. Clear English opt-outs are suppressed locally and ended by the bridge; the operator can also add any number to do-not-call. This rule-based detection does not reliably interpret every language or indirect refusal.

If a submission is interrupted or uncertain, the app holds it and blocks new calls. No automatic redial, retry, rejection-as-proof-of-failure or phone-call campaign scheduler exists. Inspect provider records. A missing confirmed conversation ID requires operator investigation; do not delete the held row to force a redial. A rejected call proposal is not recreated in the same month.

## Verification and limits

Offline tests cover provider routing, spending races, persistent history, town/month/time-zone boundaries, call approval/idempotency, suppression, unknown-send holds, custom-LLM authentication/isolation and bounded phone memory. Browser tests cover ElevenLabs playback cleanup, cancellation and visible errors. They use fake providers, not actual paid requests.

The original approved Gmail email/reply/follow-up flows are retained. This change does not claim live telephone connectivity, worldwide directory freshness, multilingual qualification, perfect opt-out understanding, inbox placement, an absolute vendor-billing cap or production deployment. Validate microphone, ElevenLabs, OpenAI and SIP behavior on your own accounts before using business outreach.
