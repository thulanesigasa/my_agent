# Phase 4: business research and qualification

## Update and open Leads

Stop the API and dashboard, then run from the same repository directory:

```powershell
git pull --ff-only
.\.venv\Scripts\python.exe -m pip install -r apps/agent/requirements.txt
npm --prefix apps/web ci
.\.venv\Scripts\python.exe -m uvicorn main:app --app-dir apps/agent --host 127.0.0.1 --port 8000
```

In a second terminal at the repository root:

```powershell
npm --prefix apps/web run dev
```

Open http://localhost:3000/dashboard and choose **Leads**. Keep your existing `.env`, Gmail credentials and SQLite data. No new API key or hosted database is required for the default workflow.

## Free discovery

1. Open https://www.openstreetmap.org and search for your target town. Zoom to the part of town you want to research.
2. The map URL contains `#map=zoom/latitude/longitude`. Copy its latitude and longitude numbers into Leads. Latitude is first; South African latitude is negative. The location label is for your own records; it does not geocode or constrain the coordinates.
3. Start with a 1 km radius and 25 results. Choose shops, food, trades/offices, or all supported categories. The maximum radius is 5 km and the maximum result count is 50.
4. Click **Discover candidates**. Results are business observations from the public Overpass API, persisted in your local ledger. The default provider is Private.coffee, whose public service permits commercial projects without registration. The UI reports if results were capped; narrow your search if so.
5. Select a candidate and open its source page. A business may have an independent website even if OpenStreetMap has no website tag. Likewise, a missing email tag means the source did not provide an email, not that the business has none.

The public service has incomplete coverage and can be unavailable or rate limited. An empty result is not proof that there are no businesses. Source retrieval time is not proof of current business activity. No Google Maps scraping, private profiles, page crawling, address guessing, email sending, or LLM call occurs in the free discovery request.

New queries have a persistent 2-minute cooldown and a default daily allowance of 20 per installation, reset by the Africa/Johannesburg calendar day. Identical queries use a provider-specific 24-hour cache, including empty results. A new-query failure consumes a request slot to avoid hammering the public service. Requests use one of two fixed HTTPS endpoints, bounded timeout, memory/output limits, no redirects, no retries and no paid fallback. API and worker share the same SQLite limits and query lease. Coordinates/radius are sent to the selected public Overpass provider; Gmail tokens and API keys are not sent with them.

Optional configuration in your existing `.env`:

```dotenv
OSM_DAILY_QUERY_LIMIT=20
OSM_PROVIDER=private_coffee
ALLOW_TAVILY_RESEARCH=false
```

The limit accepts 1–100, but leave the conservative default for this small pilot. Existing optional Tavily search tools are disabled unless both `ALLOW_TAVILY_RESEARCH=true` and `TAVILY_API_KEY` are configured. Enabling Tavily may use that provider's paid quota; it is not part of the R0 workflow. No automatic fallback enables it.

Sources: [Overpass public-service guidance](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html), [Overpass query/output documentation](https://dev.overpass-api.de/output_formats.html), and [OpenStreetMap attribution and licensing](https://www.openstreetmap.org/copyright). OpenStreetMap-derived data is © OpenStreetMap contributors and is available under the ODbL. Keep its source references and attribution when sharing derived data; the Leads screen includes the attribution link.

## Manual entry and CSV import

Use public business sources that you have reviewed yourself. Manual entry requires a business name, location label and public source URL. Optional fields are address/branch, phone, listed email, listed website and industry. Enter standard `https://` URLs. Imports cannot set verification, qualification or consent.

CSV header:

```csv
name,location,source_url,address,phone,email,website,industry
```

Only `name`, `location` and `source_url` are required columns. Paste CSV or select a file, up to 100 rows per request and 200 KB in the file picker. The complete CSV is validated before any row is written. A batch can still be interrupted by an unexpected system/storage failure; reimport safely to recover. No email is inferred from a business name/domain, and multiple possible email addresses must be reviewed rather than guessed.

OpenStreetMap records deduplicate by stable node/way/relation ID. Manual/Tavily records use normalised name, location, address and phone (plus source URL when both address and phone are missing); changing branch details can create a distinct candidate. Same-name entries in one location are flagged as possible duplicates, not automatically merged. Reject duplicates after checking the address/branch. The draft ledger also prevents repeated initial outreach to the same mailbox/contact, including previous recorded outreach.

## Evidence review

1. **Identity and activity:** verify that sources identify this business and branch, confirm it is active, and record a source URL and note. Merely appearing on a map is not enough.
2. **Website research:** search the exact name with its town/address, inspect public listings and social profiles, and record the searches/sources and any conflicting evidence. Choose one finding:

| Finding | Can qualify as a potential website client? |
| --- | --- |
| Not checked | No |
| Independent website found | No; record the URL, then keep for review or reject |
| No independent website found after review | Yes, with complete evidence; this is not proof of absence |
| Owner confirmed no website | Yes, with recorded evidence |
| Only social profiles found after review | Yes, with complete evidence; independent-site absence is still uncertain |
| Uncertain / conflicting evidence | No |

3. **Contact evidence:** record one exact published business email, its source page and how it matches this business. Tick verification only after checking it. Saving complete contact verification preserves existing consent and any do-not-contact status.
4. Choose Needs more review, Qualified, or Rejected. Qualification requires all identity/activity, website and contact evidence. Rejection requires a reason. Reviews use a revision check: if another process changed the record, reload it before saving.
5. **Permission is separate.** A qualified lead can remain blocked from drafting because permission has not been recorded. Use Settings → Contact eligibility to record actual permission and its evidence. Do not mark permission granted just because an email address is public. Keep verification selected when updating a verified contact in Settings.
6. Evidence expires for dispatch after 30 days. Recheck the actual sources, then save an updated review; do not merely renew the timestamp without checking.

Source observations keep the most recent 20 changed snapshots. Operator review history is append-only in the local ledger. Rediscovery does not replace your review with provider claims. Changed source details invalidate qualification until a new review; a rejected lead stays rejected. A source update does not change marketing consent or clear suppression.

## Preparing an outreach draft

The candidate must have current complete qualification, a verified email and recorded permission, and must not be suppressed. Connect Gmail first. Write a subject and message in the candidate's draft form, then **Save for approval**. This action sends nothing. Initial business outreach starts in Leads; Gmail Settings retains the connection test and reply forms.

Use wording supported by the evidence, such as “I couldn't find your website,” when appropriate. Portfolio matching, campaign templates, sales interpretation and follow-ups remain Phase 5. The free manual draft flow makes no LLM call. Existing conversational outreach can compose only after the same qualification and contact checks pass; any configured model provider remains subject to that provider's quota/cost.

Draft identity is stable per connected mailbox/contact, so repeated requests return the existing draft rather than overwrite reviewed content or resend it. Sent/rejected drafts are not resurrected. Prior held or sent initial outreach blocks a fresh duplicate; follow-up/campaign policies are later phases. Review the recipient, subject and body in Approvals and explicitly send. Eligibility is checked before claiming and again immediately before Gmail submission. A changed source, stale review, changed email or revoked permission blocks a previously queued lead-linked draft. Delivery-unknown sends still require reconciliation rather than resending.

Old unlinked approvals remain subject to their existing contact/consent gate; imports do not create such approvals. New lead-driven/core outreach and the Gmail outreach API use the reviewed lead path. Replies and report/test emails retain their existing separate purposes.

No business emails are sent automatically by Phase 4. The implementation is a bounded single-host pilot using SQLite, not a distributed crawler. For very large datasets, paginated storage/UI and dedicated data infrastructure belong in the later scaling work.


## Search provider errors and cooldown

The default `OSM_PROVIDER=private_coffee` uses `https://overpass.private.coffee/api/interpreter`. Its operator explicitly permits commercial use and requires no registration or API key; see [the provider's service information, terms and privacy policy](https://overpass.private.coffee/). `main` selects the original `https://overpass-api.de/api/interpreter`; review its operator's current usage policy before choosing it. Arbitrary endpoint URLs are not accepted.

There is no automatic endpoint rotation or failover. Provider selection does not reset the shared daily budget, cooldown or a provider-requested backoff. Cache entries are scoped to the selected provider. Only an operator-initiated search makes a request.

The Leads form shows the selected provider and a countdown, and disables discovery until the waiting period ends. The countdown makes no requests and does not automatically retry. A page reload restores the remaining wait from the backend. HTTP 502/503/504 is reported as provider unavailability, HTTP 429 as rate limiting, HTTP 400 as a rejected query, and connection failures as network/provider reachability problems. Failure diagnostics never expose the upstream HTML body. The API returns retry seconds plus Retry-After for cooldown/provider-backoff errors.

After repeated 502s from the original main endpoint, pull this update and restart the backend and dashboard. With no OSM_PROVIDER override, the backend will select Private.coffee automatically; if your `.env` explicitly sets `main`, change that one setting to `private_coffee`. Wait for the countdown, then try one small query. Keep existing coordinates and Gmail credentials. Both providers are external public services: availability still requires a live test on your network. A provider change is not an assurance of successful discovery.
