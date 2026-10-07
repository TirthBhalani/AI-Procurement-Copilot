# Architecture decision memo

Tirth

## Decision

Ship the single-agent workflow in auto mode for the local MVP. Keep deterministic
policy authority and visible fallback to human review.

## Evidence

Both variants used the same 16 cases. Offline, both passed 48/48 runs across three
repeats. In the live Groq experiment, both passed all six public cases. Across the
full set, A completed 15/16 runs and B 13/16. A averaged 16.56 seconds and two
model HTTP attempts; B averaged 46.63 seconds and four attempts. Each used seven
read-only tools. Retry waiting is included; these are quota-affected observations,
not controlled model-speed measurements.

B failed one overlap handoff because it omitted a catalog ID. A had one provider
429 failure; B had two. No failed run was reported as a successful live decision.

Manual review found a rounded shortfall in A, and unsupported spare-capacity and
integration claims in B. The authoritative policy findings stayed correct. New
content guards reject these defects. Replaying saved outputs accepted 14/15
completed A advisories and 11/13 B advisories, with no additional model calls.
That replay is not a fresh live experiment.

## Trade-offs

B sometimes provided broader questions or more alternatives, but a second pass
did not consistently improve grounding. It increased call volume, rate-limit
exposure and handoff complexity. A already gathers every mandatory source and
separates model interpretation from deterministic controls.

## Risks and limits

The evaluation is small, partly public and reviewed during development. Live
runs used one repeat and fixed A-before-B order. Provider limits confound latency.
The final guards have regression tests and saved-output replay, but need a fresh
live run with available quota. Pattern-based content and injection guards cannot
prove general factuality or security.

Before production, validate with Procurement/Security reviewers and unseen cases;
add identity/access control, fresh budgets, audit retention and provider governance.

## Why this MVP

One reasoning stage can interpret the use case and identify alternatives while
code handles money, dates, required reviews and evidence failures. Humans retain
approval and exception authority. Auto mode preserves a useful, grounded manual
handoff when the model fails. The second agent has not demonstrated enough
benefit to justify its extra operational cost.
