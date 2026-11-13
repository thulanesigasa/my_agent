# Automatic qualification: supported structured sources

Automation mode can now ask research jobs to qualify business facts without copying source suggestions into a manual review form. Every email still requires approval, and recipient permission remains a separate recorded requirement.

## Enable and budget

Pull and restart both servers. In **Settings → Automation mode**, enable daily research and **Automatically qualify supported research sources**. Keep your existing Tavily key and research opt-in locally. Start with **one result and four total requests** per research job. A fresh successful path uses one discovery, one primary inspection, one exact-business website/corroboration search, and one corroborating extraction. These requests share the existing daily/monthly limits, cooldown and job budget. Caches may reduce usage; failures can still consume an admitted request. There is no extra model call or paid fallback, and the code does not increase existing provider budgets.

The qualifier is enabled by default for newly created automation-mode research jobs; existing saved configurations receive this new default without resetting their version, pause state or limits. Existing jobs retain their original mode/budget and deterministic daily ID. Switching the option does not recreate today's job. Legacy manually started research jobs retain their previous inspection-only flow. A job with insufficient remaining budget records an unresolved qualification instead of making the extra requests. Existing cached inspections lacking the new structured evidence cannot qualify until a fresh bounded inspection is available (normally after the 24-hour cache expires).

## Evidence accepted by this first parser

This is a deliberately narrow implementation. It accepts explicit, single-value listing fields on the supported directory domain families (Brabys, Yellow Pages South Africa, Cylex South Africa, Snupit, Hotfrog South Africa and saYellow). **Domain membership alone is not qualification, and this implementation does not claim that every page on those services publishes these fields.** General prose, bare dates, a recent map edit or a missing website tag are not converted into verification. Source-specific adapters can be added later where a real source exposes suitable evidence.

Required labels in the extracted page are:

```text
Business name: Example Bakery
Town: Example Town
Address: 1 Main Street, Example Town
Phone: +27100000000
Email: owner@example.test
Business status: active
Activity verified: YYYY-MM-DD
Website: none
```

This is a synthetic format example, not a claim about a real business or live provider output. Labels are case-insensitive and simple Markdown bold is accepted. Duplicate labels, missing fields, multiple contacts, unsupported phone/email formats, stale/future activity dates or uncertain status values stop qualification. Activity verified must explicitly refer to activity and be within 30 SAST calendar days; a date elsewhere on a page cannot satisfy it.

The primary source must match the saved target town and candidate name. The agent searches with the exact business name, town, phone and email domain. Empty/capped searches, invalid/private URLs, an unknown possible website or failure to find a second supported directory domain keep the candidate unresolved. A subdomain or another page on the first directory is not a second domain. Supported social results are not classified as independent business websites; they cannot provide the required second directory record.

The corroborating page is extracted without following more links. Its exact returned URL must match the requested source. Name, town, street address, South African phone and email must agree across the two records. Identical copied page content is not accepted as corroboration. Both records must explicitly assert current operation with recent activity verification. A matched closure statement excludes the candidate from automated targeting. Both records must explicitly have no listed website, and the bounded search must contain only supported listing/social sources. Matching website links exclude the candidate; conflicting/unknown website fields remain unresolved.

Two domain records are corroborating source assertions, not proof of independent ownership or error-free/current facts. A bounded search cannot prove that no website exists. The proposal therefore retains the truthful wording that a website was not found in the sources reviewed and invites correction.

## Decisions and provenance

Successful reviews use `origin=automation`, never an operator-verification claim. The lead review links an immutable evidence snapshot containing literal field snippets, source URLs, content hashes, search query/results, timestamps, policy version and limitations. The source activity date remains the source's explicit date; today's fetch date does not replace it. Exclusions/unresolved cases are recorded separately and do not rewrite a human rejection or manual review. An operator decision made while a qualification step is running takes precedence.

Matching published contacts can be marked source-verified, but existing consent and suppression fields are preserved. A new contact remains `consent=unknown`. Facts can therefore be automatically qualified while outreach is still blocked for lack of genuine recorded permission. Discovery, source publication, an automated decision and your approval to send are not recorded as recipient consent.

Automation mode's existing drafting stage picks up newly qualified, permitted leads within its daily drafting cap and target filters. Its proposals and queued approvals include an **Automatic qualification · source evidence** panel. Review this together with the exact email before approving. Existing approvals keep their saved content/evidence snapshot; new qualifications do not silently rewrite them.

Automatic evidence expires after at most 24 hours (or sooner when the primary inspection expires). Current source fingerprint, inspection hash, policy version, latest qualification decision and email binding are checked by `ensure_qualified` at drafting and again on approval/provider preflight. New contradictory findings, changed inspections, expired evidence or an opt-out block further outreach; an old successful snapshot does not override them. A new supported qualification can restore current eligibility, while saved approval content remains reviewable as its original snapshot.

Research job results show automatically-qualified, excluded, unresolved and operator-preserved decisions. They are research snapshots, not delivery or sales results. Tests exercise synthetic supported sources and fake providers, including a full four-request job; no real business was qualified or contacted to validate this implementation. Your live sources may not expose the required evidence and may correctly remain unresolved.
