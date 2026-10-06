# Assessment requirement map

Source: `docs/FDE_Assessment_3.pdf`, pages 1-2, plus the starter policy and contract.

| Requirement | Implementation / evidence |
|---|---|
| Request details UI | `app.py`: samples and custom form |
| Evidence panel | UI Evidence tab, record references and tool trace |
| Recommendation and action | Decision panel and downloadable human handoff |
| At least three tools, one deterministic | Seven tools in `src/tools.py` and `src/rules.py` |
| Single-agent baseline | `src/agents.py`: one reasoning call in A |
| Staged / two-agent comparison | Analyst Advisory handed to policy/risk reviewer in B |
| Structured required outputs | `src/contracts.py`, adapter in `src/solution.py` |
| Correct approvals and budget controls | Decimal thresholds and budget rules; boundary tests |
| Existing alternatives | Catalog candidates, model fit assessment, no automatic rejection |
| Conflicting/expired vendor evidence | Independent source findings, snapshot age checks |
| Security-sensitive requests | Scope/integration checks, use-case-specific Security review |
| Missing information | Clarification/manual-verification recommendation |
| Prompt injection | Untrusted-data prompt boundary, heuristic warning, immutable authority |
| Tool/API unavailable | Failed ToolResult, no favorable fallback, manual review |
| Human escalation | No approval/mutation tool; required human reviewers and handoff |
| Same test set for A and B | `evals/compare.py`, public and extended JSON case files |
| Latency and LLM/tool counts | Telemetry, per-case CSV and summary JSON |
| Evaluation results | `evals/results/`, `docs/evaluation.md` |
| Architecture/workflow diagram | Mermaid source and rendered SVG in `docs/` |
| Assumptions and boundaries | `docs/workflow.md` and README |
| Decision memo <=500 words | `docs/architecture_decision.md` |
| One-command local start | `python run_local.py` after environment setup |
| Reproducible checks | `python scripts/verify_all.py`, dependency lock, CI workflow |
| No secrets; example configuration | Ignored `.env`, `.env.example`, historical secret scan |
| Public GitHub repository | Pending student review and publication; no push authorized |
| Google Form with public repo URL | Pending student submission; PDF states 8 October closing date |

Scoring emphasis: product/workflow and working vertical slice are represented by
the UI and real HTTP tool; architecture and reliability by the typed staged
workflow and deterministic authority; evaluation by shared cases, raw outputs,
latency/call counts and documented qualitative limitations.
