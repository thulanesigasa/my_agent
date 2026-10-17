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

## Independent-source research (recommended starting point)

Leads offers automatic Tavily web discovery alongside independent entry and manual research searches. Enter the town and business type (or a known name); the links open ordinary web searches, including searches for public business social pages. Follow the original business page and confirm the exact branch. The app does not fetch search results, scrape profiles or auto-import Google Maps listings. Save business details from independently reviewed business sources, owner-provided details or your own observations. The manual workflow needs no Google API key, billing account or new dependencies. Automatic web searches use the separately configured Tavily pilot below.

In **Add an independently sourced business**, enter the original source URL, select the source type and write a note explaining where the details came from. Source types are `business_owned_page`, `public_business_social`, `owner_provided`, `local_observation` and `other`. For a visit or owner confirmation, use an identifying public branch link and explain the independently obtained facts in the note. Source provenance stays with the observation and its history; it is not qualification, contact verification or marketing permission. The operator still performs the dated activity, website and contact review below.

Candidate source filters separate **Manual / CSV research** from OpenStreetMap and optional Tavily entries. A successful add/import selects the saved record and clears search/status filters so it remains visible. Old candidates remain in the ledger.

## Optional OpenStreetMap discovery

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

The limit accepts 1–100, but leave the conservative default for this small pilot. Tavily web research is disabled unless both `ALLOW_TAVILY_RESEARCH=true` and `TAVILY_API_KEY` are configured. It uses the bounded service described below, including when called by the core research tool. The provider account may have free or paid credits; the app cannot control account billing or usage by other installations. No automatic fallback enables it.

Sources: [Overpass public-service guidance](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html), [Overpass query/output documentation](https://dev.overpass-api.de/output_formats.html), and [OpenStreetMap attribution and licensing](https://www.openstreetmap.org/copyright). OpenStreetMap-derived data is © OpenStreetMap contributors and is available under the ODbL. Keep its source references and attribution when sharing derived data; the Leads screen includes the attribution link.

## Manual entry and CSV import

Use public business sources that you have reviewed yourself. Manual entry requires a business name, location label and public source URL. Optional fields are address/branch, phone, listed email, listed website, industry, source_kind and source_note. The manual UI requires a source type and note; API/CSV requests without these fields remain backward compatible, with provenance shown as not recorded. A selected source kind requires a nonblank note. Existing evidence and permission checks still apply to every candidate. Enter standard `https://` URLs. Imports cannot set verification, qualification or consent.

CSV header:

```csv
name,location,source_url,address,phone,email,website,industry,source_kind,source_note
```

Only `name`, `location` and `source_url` are required columns. Paste CSV or select a file, up to 100 rows per request and 200 KB in the file picker. The complete CSV is validated before any row is written. A batch can still be interrupted by an unexpected system/storage failure; reimport safely to recover. No email is inferred from a business name/domain, and multiple possible email addresses must be reviewed rather than guessed.

OpenStreetMap records deduplicate by stable node/way/relation ID. Manual/Tavily records use normalised name, location, address and phone (plus source URL when both address and phone are missing); changing branch details can create a distinct candidate. Same-name entries in one location are flagged as possible duplicates, not automatically merged. Reject duplicates after checking the address/branch. The draft ledger also prevents repeated initial outreach to the same mailbox/contact, including previous recorded outreach.

## Evidence review

1. **Identity and activity:** verify that sources identify this business and branch, confirm it is active, and record a source URL and note. Choose dated public business activity, direct confirmation, or personally observing the branch operating. Enter the date of that evidence (within the last 30 days by the SAST calendar), not the date you looked up an old listing. Public activity evidence must use a source other than OpenStreetMap, such as a dated business post. For a call or visit, describe the confirmation/observation in the note; the identity URL can still point to the branch listing. Missing, future or expired activity dates block qualification and dispatch, including previously saved qualifications. Saving a review again does not renew the activity evidence date.
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

## Outdated or closed listings

OpenStreetMap is a source of candidates, not a current business directory. Different Overpass providers serve the same underlying source. The screen now distinguishes the last map edit, the mapper’s check/survey tag (when supplied), and the date this app retrieved the listing. Map edits over a year old receive an additional warning. Even a recent edit may have changed only an unrelated detail; neither an edit nor a mapper tag proves the business is trading. Unknown dates stay unknown. Older stored results remain usable for review without a database migration; run discovery after the cooldown to retrieve metadata. The cache version changes once for this update, without resetting request limits.

If you know a branch has closed, select **Inactive / closed**, **Rejected / duplicate / unsuitable**, enter a decision note explaining your knowledge, and **Save review**. No contact or website evidence is needed for rejection. Rediscovery preserves that rejection. Check the branch/address before rejecting a same-name business elsewhere. Use **Needs review** to focus on unreviewed candidates.

For missing or inaccurate map coverage, use **Add a business manually** or **Import CSV** with sourced businesses you have researched. No additional paid provider or API key is introduced. The app records operator evidence; it does not automatically authenticate posts, phone calls or visits. Current operation is verified separately from whether the business lacks a website and whether contact permission exists.

## Why this update does not integrate Google Places

Google Maps may provide more useful local listings than OpenStreetMap, but it is not a drop-in source for this durable outreach ledger. The standard [Maps Platform terms, section 3.2.3](https://cloud.google.com/maps-platform/terms) restrict exporting/storing Maps business content and using the services to create or augment advertising products. The [Places policies](https://developers.google.com/maps/documentation/places/web-service/policies) also limit storage, with exceptions such as place IDs. A place-ID exception does not by itself authorize copying listings into an outreach database. Google API discovery would require a separate licensing/design assessment before implementation.

The selected alternative saves independently sourced operator evidence. No Google API setting, key or billing setup is required. Search links are navigation aids and do not import search-engine snippets or Maps content. Source classification is an operator statement, not automated authentication or a license grant for third-party content.

## Automatic web discovery pilot (Tavily)

1. Pull this update and stop/restart both servers. No new dependencies are required.
2. Create a free Tavily account and keep paid/pay-as-you-go usage disabled. Keep the key local; do not share it or screenshots of it. In your existing backend `.env`, set:

```dotenv
TAVILY_API_KEY=your_local_key
ALLOW_TAVILY_RESEARCH=true
TAVILY_DAILY_QUERY_LIMIT=5
TAVILY_MONTHLY_QUERY_LIMIT=100
```

3. Restart the backend after editing `.env`. In Leads, open **Automatic web discovery · Tavily**. The panel shows whether the key is configured and research is enabled, but never returns the key. Enter `Standerton, Mpumalanga`, `plumbers`, and 5 source results; click **Discover web candidates** once. Only the town/type query is sent to Tavily, not Gmail credentials or conversation content.
4. Returned candidates appear in the **Tavily** source filter. Open each original source and verify the business/branch. Search titles may be directory headings, not business names: qualification additionally requires a **Confirmed business and branch name**. A result does not establish current activity, website absence, a contact email, or consent. Emails are never guessed or extracted from snippets.
5. Discard unrelated/directory results with a rejection reason, or manually enter separately verified individual businesses. Complete the existing dated activity, website and exact contact review, then record actual contact permission before preparing outreach. Searching never sends emails.

Every new query makes at most one fixed-endpoint basic search with auto-parameters, provider answers, raw content and images disabled. There is no crawling, extraction endpoint, LLM call, retry or fallback. Results are limited to 1–10, with a 40-second total network deadline, no redirects, and a 2 MB response limit. Invalid source links/results are skipped. Only bounded titles, source links and operator evidence are saved; snippets/raw responses/keys are not stored in the lead ledger. Source URLs deduplicate Tavily results across queries and title changes, including previous records; a title/query change can invalidate qualification but cannot resurrect rejection. Confirmed operator names survive rediscovery.

Local limits default to 5 new attempts per SAST day and 100 per SAST calendar month (configurable up to 20/day and 500/month), shared by API and worker through SQLite. A 2-minute persisted cooldown and shared lease prevent concurrent bursts. Attempts are reserved before network I/O: failures and interrupted attempts count conservatively. Identical town/type/limit searches use a 24-hour cache, including empty results; cached reads consume no extra attempt and remain available after local budgets are reached. Disabling research or removing the key blocks new research calls, including cache access, without deleting saved leads. These are local attempted-request counters, not the provider's remaining-credit balance. Calendar resets may differ from the provider's credit cycle. Check the Tavily dashboard and other API-key usage separately.

Provider HTTP 401/403 reports a credential/access problem without leaking upstream bodies; 429 honors an integer Retry-After (at least two minutes, capped at one day); 432/433 reports provider account limits. No error enables paid usage. Failed attempts still consume a local slot; the panel restores cooldown/counters after reload. The default basic-search credit expectation is based on [Tavily's current credit documentation](https://docs.tavily.com/documentation/api-credits), not a guarantee of perpetual free service. Review the [provider terms](https://www.tavily.com/terms) and original sources; API access does not grant unrestricted rights to third-party pages.

The tests use fake responses and no external credentials. Successful local offline tests do not establish live coverage or availability in Standerton. Test a small query on your own account before scaling. For account-wide cost control, keep paid usage disabled at the provider; local limits cannot prevent charges caused by other clients or account settings.
