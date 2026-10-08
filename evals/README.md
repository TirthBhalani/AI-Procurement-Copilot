# Evaluation guide

Use `python evals/compare.py --mode offline --repeat 3` for the non-billable
comparison, or `python evals/compare.py --mode live --pause 10 --output-dir evals/results/live_rerun`
for Groq reasoning while preserving earlier evidence.
The runner manages a local mock API when one is not already running. It reuses an
existing service and stops only a process it created.

The same six public cases and ten extended cases run on both architectures.
Extended cases include four unused starter requests and six modified requests
with new IDs. Expected approvals/actions live in the case definitions, not in
solution code. The case-set digest lets readers verify that both modes used the
same cases. Public expectations remain unchanged.

## What the checks establish

- Starter schema and minimum approval/risk/missing-information expectations.
- Expected next-action labels and forbidden approval additions on selected cases.
- Evidence references resolve to known files/record IDs; catalog product names
  and available-budget amounts agree with the referenced records.
- Human review stays required.
- Live runs actually completed model reasoning; a fallback is a failed live run.
- End-to-end latency includes tool gathering, model calls and retries. The
  inter-case `--pause` is outside the timing window.
- `llm_calls` counts HTTP attempts, including retries. Successful A normally needs
  one reasoning stage and B two; tools are invoked seven times on both paths.

These checks are not a complete factuality or security proof. They do not grade
every generated sentence, every possible semantic overlap, or every missing
policy condition. Unit tests cover deterministic boundaries, malformed inputs,
API failures, injection, secret redaction and invalid model handoffs. The
qualitative review in `docs/evaluation.md` considers actual model interpretation.

## Output files

Each mode writes `comparison.csv`, `decisions.json`, and `summary.json` under
`evals/results/<mode>/`. Reports include failures and use actual run timestamps.
A run replaces its output directory's earlier report. Use a new `--output-dir`
to preserve a previous experiment. Reports are checkpointed after each attempt.
An explicit daily provider quota error stops the comparison and sets
`status=blocked_provider_quota`; `attempted_runs` can be smaller than
`planned_runs`. Exit code 2 signals that blocker. Unattempted cases have no
latency or pass/fail result. A `running` status also means an incomplete run.

The supplied public runner remains compatible:

```sh
python evals/run_public_evals.py --architecture single
python evals/run_public_evals.py --architecture staged
```

It requires the mock API to be running and follows `COPILOT_MODE` from the
environment. It checks minimum behavior, not complete grading criteria. The
committed `offline/public_single.csv` and `offline/public_staged.csv` were run
with `COPILOT_MODE=offline`; they must not be described as model evaluations.

Read `docs/evaluation.md` for results, failure analysis, measurement limitations
and the architecture choice. The final memo is in `docs/architecture_decision.md`.
