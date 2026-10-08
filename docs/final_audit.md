# Requirements audit

Tirth

Reviewed on 11 October 2026 against both supplied PDFs, the starter policy,
the output contract, the source, and the saved evaluation evidence.

## Rubric coverage

| Assessment area | Weight | Local implementation and evidence |
|---|---:|---|
| Product and workflow | 15% | Sample/custom requests, request details, cited evidence, recommendation, next action and downloadable human handoff in `app.py` |
| End-to-end product | 20% | One-command launcher, Streamlit UI, real HTTP vendor-risk retrieval, configured Groq reasoning and structured review package |
| Agent and tool design | 20% | A single procurement agent; B analyst/reviewer with typed handoff and original evidence; seven read-only deterministic tools |
| Reliability and human controls | 15% | Decimal thresholds, budget checks, review-date checks, incomplete/conflicting/unavailable evidence, injection boundaries, secret redaction and human-only approval |
| Evaluation and comparison | 20% | Identical 16-case set for both architectures, raw decisions and failures, reference checks, latency and HTTP/tool counts, qualitative review and evidence-backed ship decision |
| Engineering and communication | 10% | Locked dependencies, regression tests, verification script, CI configuration, README, assumptions, rendered Mermaid diagram, demo and decision memo |

These weights are the published rubric, not predicted marks. Local coverage
does not establish an assessor's score or submission eligibility.

## Fixes found during this audit

- Live mode now fails explicitly when policy is unavailable, without making a
  model call. Auto mode displays the manual-review hold.
- Invalid reference dates are treated as unavailable policy rather than causing
  an uncaught date-parsing error.
- Confidential use stated in business-purpose text now triggers Privacy and
  Legal review when overseas storage is reported, even if the access field
  incorrectly says public.
- The comparison accepts `--output-dir` so fresh results can be saved without
  replacing the original experiment and its documented failures.
- Evaluation progress is checkpointed after each attempted run. Explicit daily
  provider quota exhaustion stops the comparison and marks its report partial.
- Model citations must refer to evidence actually supplied to the model.
  Withheld employee identity records cannot be cited as model evidence.

Each control fix has a regression test.

## Verification

- Preflight and all 61 automated tests pass.
- Both architectures pass 48/48 offline cases over three repeats: 96 runs total.
- Saved-output replay rejects the three documented narrative defects.
- Dependency consistency, Python compilation and local Markdown links pass.
- The decision memo is below 500 words; the Mermaid diagram renders legibly.
- The starter datasets are unchanged.
- `.env` is ignored; no Git remote is configured and nothing has been pushed.

The commands and detailed measurements are in `README.md` and `evaluation.md`.

The current-code live audit passed five checks, then encountered two quota
failures before being stopped. Groq explicitly reported daily token exhaustion.
A follow-up run verified immediate quota detection and saved a partial report
after one failed attempt; 31 planned runs were not attempted. The full earlier
comparison is preserved, but a complete live comparison of the latest code
remains blocked by provider quota. See `evaluation.md` for the evidence limits.

## Submission work outside the local project

The required public GitHub URL and Google Form submission remain pending the
student's review. The supplied assessment states a closing date of 8 October
2026; this audit is dated 11 October 2026. Submission eligibility needs to be
confirmed with the course. Git commits record their actual creation dates.

The local product has no purchasing or approval capability. Production features
such as authentication, budget reservation and an approval ledger are outside
this assessment MVP and are documented limitations.
