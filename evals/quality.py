"""Independent reference checks, separate from the decision implementation."""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def grounded_references(decision):
    keys = {'employees.csv':'employee_id', 'software_catalog.csv':'software_id',
            'vendors.csv':'vendor_id', 'purchase_history.csv':'purchase_id',
            'department_budgets.csv':'department'}
    for evidence in decision.evidence:
        ref = evidence.reference or ''
        if ref.startswith('/vendor-risk/'):
            if evidence.source != 'vendor_risk':
                return False
        elif ':' in ref and ref.split(':', 1)[0] in keys:
            file, identity = ref.split(':', 1)
            with (ROOT/'data'/file).open(encoding='utf-8', newline='') as stream:
                rows = list(csv.DictReader(stream))
            record = next((r for r in rows if r[keys[file]] == identity), None)
            if not record:
                return False
            if file == 'software_catalog.csv' and record['product_name'] not in evidence.finding:
                return False
            if file == 'purchase_history.csv' and record['product_name'] not in evidence.finding:
                return False
            if file == 'department_budgets.csv':
                available = f"${float(record['available_usd']):,.2f}"
                if available not in evidence.finding:
                    return False
        elif 'procurement_policy.md' in ref:
            if not (ROOT/'data/procurement_policy.md').exists():
                return False
        elif ref == 'software_catalog.csv':
            pass
        elif ref in {'requester_budget','catalog','registry','history','vendor_risk','policy'}:
            if 'unavailable' not in evidence.finding.lower():
                return False
        else:
            return False
    return bool(decision.evidence)
