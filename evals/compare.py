"""Run the same cases on both architectures against the real local mock API."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import requests
from evals.run_public_evals import evaluate
from evals.quality import grounded_references
from run_local import wait_for_api
from src.agents import model_settings
from src.contracts import ProcurementDecision
from src.data_access import get_request
from src.solution import analyze_request


@contextmanager
def local_api():
    proc = None
    url = 'http://127.0.0.1:8001'
    os.environ['VENDOR_RISK_BASE_URL'] = url
    try:
        try:
            response = requests.get(url + '/health', timeout=1)
            response.raise_for_status()
        except requests.RequestException:
            proc = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'mock_api.app:app',
                                     '--host', '127.0.0.1', '--port', '8001', '--log-level', 'error'], cwd=ROOT)
            wait_for_api(url + '/health', proc)
        yield
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()


def percentile95(values):
    ordered = sorted(values)
    return ordered[min(len(ordered)-1, int(len(ordered)*0.95))]


def save_reports(output, rows, outputs, *, mode, case_hash, case_count, repeats, status):
    with (output/'comparison.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (output/'decisions.json').write_text(json.dumps(outputs, indent=2), encoding='utf-8')
    summary = dict(mode=mode, model=model_settings()[1] if mode == 'live' else None,
                   provider=model_settings()[0] if mode == 'live' else None,
                   generated_at=datetime.now(timezone.utc).isoformat(), case_set_sha256=case_hash,
                   distinct_cases=case_count, repeats=repeats, status=status,
                   planned_runs=case_count*repeats*2, attempted_runs=len(rows), architectures={})
    for arch in ['single', 'staged']:
        selected = [r for r in rows if r['architecture'] == arch]
        times = [r['latency_ms'] for r in selected]
        summary['architectures'][arch] = dict(passed=sum(r['passed'] for r in selected), total=len(selected),
            mean_latency_ms=round(statistics.mean(times),2) if times else None,
            median_latency_ms=round(statistics.median(times),2) if times else None,
            p95_latency_ms=round(percentile95(times),2) if times else None,
            mean_llm_calls=statistics.mean(r['llm_calls'] for r in selected) if selected else None,
            mean_tool_calls=statistics.mean(r['tool_calls'] for r in selected) if selected else None)
    (output/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['offline', 'live'], default='offline')
    parser.add_argument('--repeat', type=int, default=1)
    parser.add_argument('--public-only', action='store_true')
    parser.add_argument('--pause', type=float, default=0, help='Seconds between calls for provider rate limits')
    parser.add_argument('--output-dir', type=Path, help='Separate report directory; defaults to evals/results/<mode>')
    args = parser.parse_args()
    if not 1 <= args.repeat <= 10:
        parser.error('--repeat must be between 1 and 10')
    if args.pause < 0:
        parser.error('--pause must be nonnegative')
    paths = [ROOT/'evals/public_cases.json']
    if not args.public_only:
        paths.append(ROOT/'evals/extended_cases.json')
    cases = [case for path in paths for case in json.loads(path.read_text(encoding='utf-8'))]
    case_hash = hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest()
    output = args.output_dir or ROOT/'evals'/'results'/args.mode
    output.mkdir(parents=True, exist_ok=True)
    rows, outputs = [], []
    quota_blocked = False
    with local_api():
        for repeat in range(args.repeat):
            for case in cases:
                for arch in (['single','staged'] if repeat % 2 == 0 else ['staged','single']):
                    req = dict(get_request(case['request_id']))
                    req.update(case.get('overrides', {}))
                    started = time.perf_counter()
                    row = dict(case_id=case['case_id'], architecture=arch, repeat=repeat+1,
                               mode=args.mode, passed=False, correct_next_action=False,
                               grounded_references=False, policy_followed=False,
                               human_escalation_correct=False, llm_calls=0, tool_calls=0)
                    try:
                        decision = ProcurementDecision.model_validate(analyze_request(req, arch, mode=args.mode).model_dump())
                        failures = evaluate(decision, case['expectations'])
                        public_actions = {'PUB-01':'existing', 'PUB-02':'specialist', 'PUB-03':'specialist',
                                          'PUB-04':'budget', 'PUB-05':'clarification', 'PUB-06':'clarification'}
                        expected_action = case.get('action_contains', public_actions.get(case['case_id'], ''))
                        action_ok = bool(expected_action) and expected_action.lower() in decision.recommendation.lower()
                        forbidden = set(case.get('forbidden_approvals', [])) & set(decision.required_approvals)
                        refs_ok = grounded_references(decision)
                        if not action_ok:
                            failures.append('unexpected next-action label')
                        if forbidden:
                            failures.append('unexpected approvals: ' + ', '.join(sorted(forbidden)))
                        if args.mode == 'live' and decision.execution_mode != 'live_model':
                            failures.append('live model did not complete')
                        if not refs_ok:
                            failures.append('uncited evidence')
                        row.update(passed=not failures, correct_next_action=action_ok,
                                   grounded_references=refs_ok, policy_followed=not evaluate(decision, case['expectations']) and not forbidden,
                                   human_escalation_correct=decision.human_review_required,
                                   llm_calls=decision.telemetry.llm_calls, tool_calls=decision.telemetry.tool_calls,
                                   failures=' | '.join(failures))
                        outputs.append(dict(case_id=case['case_id'], architecture=arch, repeat=repeat+1,
                                            request=req, decision=decision.model_dump()))
                    except Exception as exc:
                        row['failures'] = str(exc) if type(exc).__name__ == 'ModelUnavailable' else type(exc).__name__
                        quota_blocked = getattr(exc, 'daily_quota_exhausted', False) is True
                        if hasattr(exc, 'telemetry'):
                            row.update(llm_calls=exc.telemetry.llm_calls, tool_calls=exc.telemetry.tool_calls)
                    row['latency_ms'] = round((time.perf_counter()-started)*1000, 2)
                    rows.append(row)
                    summary = save_reports(output, rows, outputs, mode=args.mode, case_hash=case_hash,
                        case_count=len(cases), repeats=args.repeat,
                        status='blocked_provider_quota' if quota_blocked else 'running')
                    print(f"{'PASS' if row['passed'] else 'FAIL'} {case['case_id']} {arch} {row['latency_ms']:.0f}ms {row['failures']}", flush=True)
                    if quota_blocked:
                        break
                    if args.pause:
                        time.sleep(args.pause)
                if quota_blocked:
                    break
            if quota_blocked:
                break
    summary = save_reports(output, rows, outputs, mode=args.mode, case_hash=case_hash,
        case_count=len(cases), repeats=args.repeat,
        status='blocked_provider_quota' if quota_blocked else 'completed')
    print(json.dumps(summary, indent=2))
    if quota_blocked:
        print('Daily provider quota exhausted; remaining cases were not attempted. Partial reports saved.')
        return 2
    return 0 if all(r['passed'] for r in rows) else 1


if __name__ == '__main__':
    raise SystemExit(main())
