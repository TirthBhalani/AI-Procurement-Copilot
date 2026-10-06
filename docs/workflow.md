# Workflow and assumptions

Tirth

![Architecture](architecture.svg)

The editable source is [architecture.mmd](architecture.mmd). The SVG is rendered
with Mermaid CLI; GitHub can also render the Mermaid block in the README.

Optional regeneration, with Node.js installed:

```sh
npx --yes --package @mermaid-js/mermaid-cli mmdc -i docs/architecture.mmd -o docs/architecture.svg -b white
```

The committed SVG needs no editor extension to display.

## Request to handoff

1. Select a sample or enter a custom request. Unknown values remain unknown.
2. Gather all six evidence sources. Mandatory retrieval is orchestrated in code,
   rather than allowing a model to skip an unfavorable source.
3. Run the seventh tool, `policy_rules`. Money comparisons use Decimal; review
   ages use the policy reference date, not today's date.
4. A single agent interprets the evidence, or an analyst hands a typed Advisory
   to a reviewer. Both stages use the same model, policy, catalog and source facts.
5. Validate structured output, evidence indices and catalog IDs. Keep all rule
   approvals and flags. Models can propose additional reviews and alternatives.
6. Show the decision and export a review package. Humans resolve gaps, review
   alternatives, grant exceptions and approve outside the app.

## Tool boundaries

| Tool | Input | Output | Failure behavior |
|---|---|---|---|
| requester_budget | requester ID | Employee department and budget snapshot | Finance/manual verification |
| catalog | product, vendor, category | Approved catalog and exact/category matches | Catalog verification required |
| registry | vendor name | Internal procurement, security and terms status | Onboarding and specialist review |
| history | vendor name | Prior purchases with record IDs | Manual history verification |
| vendor_risk | vendor name | HTTP assessment, dates, storage and risk signals | No backing-file fallback; Security review |
| policy | no business input | Policy text, reference date, digest | Stop; Procurement restores policy |
| policy_rules | EvidencePack | Mandatory controls and cited findings | No purchase capability |

All tools are deterministic/read-only. LLM calls are counted separately from tool
invocations. The model interprets use-case fit and semantic risk; it does not do
approval arithmetic. Provider calls are bounded, timed out and schema validated.
HTTP 429 permits retries using Retry-After (capped at 60 seconds); a provider
schema-generation error also permits a retry. There are at most three attempts
per stage, and each HTTP attempt counts as an LLM call. Other failures are not
retried. Auto mode surfaces a rules-only fallback; live mode fails
the run if either required reasoning stage fails.

## Handoff contract

`EvidencePack` contains the original request and six `ToolResult` objects. Each
has `name`, `ok`, `data`, and a sanitized error type. `Advisory` contains a use-case
summary, overlap assessment, catalog IDs, numbered evidence references, proposed
additional reviewers and questions. B's reviewer receives that analyst handoff
alongside the original source evidence, not just an analyst paraphrase.

`ProcurementDecision` preserves the starter contract and adds execution mode,
model name, warnings, advisory and stage trace. Evidence is assembled from tool
records and policy checks. Model interpretation is displayed separately; a valid
citation index does not prove every generated sentence is factually correct.

## Assumptions

- All supplied business records are synthetic. A data-access field such as
  `customer_pii` describes intended future access; no customer records are present.
- Cost is the total annualized USD amount, including one-time services as given.
  The UI does not silently convert monthly charges or currencies. Zero-cost
  requests still require the applicable human approval.
- Policy 2026.09 is implemented in code. An unsupported version stops review and
  needs a reviewed rules update. Reference date is extracted from the policy; review age 365 days is
  current, 366 days expired. Future or malformed dates require Security review.
- The employee directory determines department; contradictory input is surfaced.
- Total licensed seats do not establish unused capacity. Scope and entitlement
  must be checked by Procurement, including add-ons and training agreements.
- Product/vendor/category matches are conservative candidate overlap, not rejection.
  The model can nominate other catalog entries based on the stated use case.
- Vendor personal-data capability alone does not prove this request processes PII.
  PII request scope triggers Privacy. Overseas storage plus sensitive/unknown
  scope adds Privacy and Legal. No unsupported operating-region inference is made.
- Approved vendor status does not waive security review for sensitive scope.
- Draft, unknown or missing terms require Legal. A missing registry record is
  treated as unverified onboarding, never as an approved vendor.
- Injection detection is a warning heuristic, not the security boundary. The
  model has no tools for purchase, budget mutation or approval. Rules cannot be
  removed by the model, and untrusted text is placed only in the data payload.
- Hosted model payloads omit employee identity/reporting records. No environment
  values or API keys enter prompts, traces or downloadable packages.
- Redaction removes configured key values and common API-token patterns from
  requests, tool outputs and model responses. This is best-effort protection,
  not a general classifier for arbitrary sensitive data.

## Deliberate limits

No purchasing integration, authentication, persistent approval store, multi-user
budget reservations, RAG/vector database, or autonomous workflow delegation.
This is a local assessment MVP. Production needs authorization, audit retention,
data minimization, provider governance, fresh budgets and formal policy ownership.
