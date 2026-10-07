# Submission checklist

Tirth

## Local deliverables

- [x] Preflight passes in the project environment.
- [x] Working product UI: request, evidence, recommendation and downloadable handoff.
- [x] One-command launcher starts the loopback API and UI; both health checks pass.
- [x] Working single-agent A and staged analyst/reviewer B.
- [x] Seven read-only tools, including deterministic policy checks.
- [x] Required ProcurementDecision adapter and structured outputs.
- [x] Budget, financial thresholds and vendor-date boundary tests.
- [x] Missing, conflicting, stale and unavailable evidence is surfaced.
- [x] Human authority preserved; no purchase, approval or budget mutation capability.
- [x] Request/vendor injection is treated as untrusted data.
- [x] Date checks use policy reference date 2026-09-30.
- [x] Same 16 cases attempted on both architectures; failures retained.
- [x] Raw results, latency, model HTTP attempts and tool counts are committed.
- [x] Narrative defects are disclosed and rejected by tested final guards/replay.
- [x] Decision memo is 358 words, below the 500-word limit.
- [x] Mermaid source and rendered diagram verified.
- [x] Setup, assumptions, known limitations and ship decision documented.
- [x] Locked dependencies and repeatable verification script supplied.
- [x] Environment file ignored; secret scan covers tracked files and Git history.
- [x] No Git remote configured and nothing pushed.

## Student actions

- [ ] Review the app, report and source; understand the architecture decision.
- [ ] Optionally rerun the final live comparison with available Groq quota.
      Preserve the earlier results folder first. Final guards were verified by
      tests and saved-output replay; a fresh post-guard live result is not claimed.
- [ ] Create/link the intended public GitHub repository and publish after review.
- [ ] Verify `.env` is still ignored and run the secret scan before publishing.
- [ ] Submit the public repository URL through the assessment Google Form.
- [ ] Confirm submission eligibility: the supplied PDF lists 8 October 2026 as
      the closing date. Local implementation/commits use their actual dates.

Run `python scripts/verify_all.py` for the non-billable verification path. The
CI workflow is configured but has not run on GitHub because nothing was pushed.
