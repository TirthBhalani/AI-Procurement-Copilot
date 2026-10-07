# Evaluation results

## Method

Both architectures used the same six public cases plus ten extended cases
(case-set SHA256 `f544a3ccb67772566a8c8eb94aec4c5bbe5476cfe64a238a3e5111f7bd78f271`).
The extended set covers unused starter requests and unseen IDs/values. The
vendor-risk tool made real HTTP calls to the local mock API, including its
intentional 503 response. Nothing was purchased or approved.

Offline comparison: three repeats, 48 runs per architecture. Live comparison:
one repeat, 16 runs per architecture, Groq `openai/gpt-oss-120b`, temperature 0,
low reasoning effort. A ran before B for each case. The configured 10-second
pause between runs is excluded from latency; provider retry waiting is included.

## Measured results

| Metric | Single A | Staged B |
|---|---:|---:|
| Offline checks passing | 48/48 | 48/48 |
| Live public minimum/structural checks passing | 6/6 | 6/6 |
| Live full-set completions passing checks | 15/16 | 13/16 |
| Mean live latency | 16.56 s | 46.63 s |
| Median live latency | 10.09 s | 34.96 s |
| p95 live latency | 123.12 s | 132.47 s |
| Mean model HTTP attempts per run | 2.00 | 4.00 |
| Reasoning stages without retries | 1 | 2 |
| Tool invocations per run | 7 | 7 |

`llm_calls` counts HTTP attempts, including rejected/retried requests, not just
successful inferences. Failures remain in the CSV and latency aggregates. The
provider's 8,000-token/minute limit was observed during diagnostics; the later
HTTP 429 failures are recorded as rate/quota failures without guessing their
precise cause. This small, serial run does not establish intrinsic model speed.

The live files preserve the original experiment before the final content guards.
They must not be presented as a fresh live evaluation of those later guards.

## Failures and qualitative findings

| Case | Finding | Control / response |
|---|---|---|
| EXT-05, B | Overlap assessment lacked a catalog ID | Original validator rejected the handoff; live run failed |
| EXT-09, B | Groq HTTP 429 after bounded retries | No live result fabricated |
| EXT-10, A and B | Groq HTTP 429 after bounded retries | No live result fabricated |
| PUB-05, B | Summary claimed spare capacity although only total licensed seats are known | Added content guard; saved output rejected on replay |
| EXT-05, A | Question rounded the $10,000.01 shortfall to $10,000 | Added exact Decimal shortfall validation |
| EXT-08, B | Summary described missing integrations as none | Added missing-versus-empty integration guard |

The authoritative budget findings, approval lists, risk flags and missing fields
remained grounded in deterministic tools. The three narrative defects show why
reference validation alone is insufficient. Current guards reject these known
claim patterns; auto mode then returns the rules-only human handoff with a
visible warning. Live mode fails explicitly.

Other completed interpretations generally matched the stated need and posed
useful questions about capacity, scope, integrations and specialist review. A
and B both identified existing software without automatically rejecting a new
request. In PUB-02, B listed both design alternatives while A nominated one and
asked about both. In PUB-06, both nominated limited-use NeuralDesk as a possible
alternative requiring validation, not authorization for confidential data.
Some advisories repeated already-required reviewers; the merge kept them unique.

## Current guard replay

`python evals/replay_guards.py` re-gathers the unchanged synthetic evidence and
validates saved completed advisories. It makes **zero model calls**.

| Replay result | Single A | Staged B |
|---|---:|---:|
| Saved completed outputs screened | 15 | 13 |
| Accepted by current guards | 14/15 | 11/13 |
| Accepted relative to all attempted cases | 14/16 | 11/16 |

See `evals/results/live/guard_replay.csv` and `manual_review.csv`. This replay
is a regression screen after inspecting the outputs, not an independent held-out
study. The original failed runs are not silently converted into passes.

## Verification and reproducibility

The project has 55 automated tests covering source integrity, financial/date
boundaries, tool failures, model handoffs, injection, redaction, UI state, evidence
references and the new narrative guards. The original public harness also passes
6/6 on both adapters in explicit offline mode. `python scripts/verify_all.py`
reruns preflight, tests, repeated offline comparison and historical secret scan.
The one-command launcher was verified with both loopback services healthy.

Raw reports live in `evals/results/offline` and `evals/results/live`. Repeat the
live command with available Groq quota to test current guards on newly generated
outputs; preserve the old folder before rerunning. No post-guard fresh live
comparison is claimed here.

## Decision and limits

Ship A with auto mode for this local MVP. B added latency, provider attempts and
a handoff failure without improving deterministic policy compliance. The final
replay also accepted fewer of B's narratives. This supports choosing the simpler
workflow, not a claim that every single-agent system is better.

The set is small, partly public and inspected during development. One live
repeat, fixed A-before-B order, temperature-0 nondeterminism and provider limits
confound the comparison. The guards catch specific unsupported claims, not all
hallucinations. Production still needs fresh budgets, authentication, audit
retention, stronger grounding checks and review by procurement specialists.
