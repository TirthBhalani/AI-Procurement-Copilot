"""Screen saved live interpretations with current guards; makes no model calls."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from evals.compare import local_api
from src.agents import Advisory, ModelUnavailable, validate_advisory
from src.rules import apply_rules
from src.telemetry import RunTelemetryCounter
from src.tools import gather


def main():
    folder = ROOT/'evals/results/live'
    saved = json.loads((folder/'decisions.json').read_text(encoding='utf-8'))
    rows = []
    with local_api():
        for item in saved:
            pack = gather(item['request'], RunTelemetryCounter())
            row = dict(case_id=item['case_id'], architecture=item['architecture'],
                       current_guards_pass=True, failure='', model_calls=0)
            try:
                validate_advisory(Advisory.model_validate(item['decision']['advisory']), pack, apply_rules(pack))
            except ModelUnavailable as exc:
                row.update(current_guards_pass=False, failure=str(exc))
            rows.append(row)
    with (folder/'guard_replay.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    for arch in ('single','staged'):
        selected = [r for r in rows if r['architecture'] == arch]
        print(f"{arch}: {sum(r['current_guards_pass'] for r in selected)}/{len(selected)} saved completed outputs pass current guards")
    for row in rows:
        if not row['current_guards_pass']:
            print(row['case_id'], row['architecture'], row['failure'])
    print('Replay is a regression screen, not a fresh live run or independent quality study.')
    review_file = folder/'manual_review.csv'
    if review_file.exists():
        completed = {(r['case_id'], r['architecture']) for r in rows}
        with review_file.open(encoding='utf-8', newline='') as stream:
            expected = {(r['case_id'], r['architecture']) for r in csv.DictReader(stream)
                        if r['grounded_evidence'] == 'False' and (r['case_id'], r['architecture']) in completed}
        rejected = {(r['case_id'], r['architecture']) for r in rows if not r['current_guards_pass']}
        if rejected != expected:
            raise SystemExit('Guard replay differs from the documented qualitative review.')
        print('Known narrative defects were rejected as expected.')


if __name__ == '__main__':
    main()
