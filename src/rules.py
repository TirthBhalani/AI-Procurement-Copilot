"""Deterministic policy controls for assessment policy 2026.09."""
from __future__ import annotations

import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation

from src.contracts import EvidenceItem, ProcurementDecision
from src.tools import EvidencePack, normal


def amount(value: object) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = Decimal(str(value))
        return number if number.is_finite() and number >= 0 else None
    except (InvalidOperation, ValueError):
        return None


def business_approvals(cost: Decimal) -> list[str]:
    if cost <= 1000:
        return ["Manager"]
    if cost <= 10000:
        return ["Department Head", "Procurement"]
    if cost <= 25000:
        return ["Department Head", "Finance", "Procurement"]
    return ["Department Head", "Finance", "CFO", "Procurement"]


def review_state(status: object, reviewed: object, reference: date) -> str:
    try:
        age = (reference - date.fromisoformat(str(reviewed))).days
    except (ValueError, TypeError):
        return "missing_date"
    if age < 0:
        return "future_date"
    if age > 365:
        return "expired"
    return "current" if normal(status) == "approved" else "not_approved"


def suspicious(text: str) -> bool:
    patterns = [r"ignore.{0,60}(rules|policy|instructions|procurement)",
                r"(bypass|override).{0,40}(approval|security|policy|control)",
                r"(cfo|pre)[ -]?approved", r"approve.{0,25}immediately",
                r"(reveal|expose|print|send).{0,40}(secret|api.key|password)",
                r"system\s*(prompt|message)|<\|.*?\|>"]
    return any(re.search(p, text, re.I | re.S) for p in patterns)


KNOWN_ACCESS = {"none", "public", "internal_documents", "internal_marketing",
                "source_code", "production_telemetry", "confidential_documents",
                "employee_pii", "customer_pii", "credentials", "secrets"}


def apply_rules(pack: EvidencePack) -> ProcurementDecision:
    req = pack.request
    decision = ProcurementDecision(request_id=str(req.get("request_id", "CUSTOM")),
                                   recommendation="Route for human review", next_step="")
    approvals, flags, missing = decision.required_approvals, decision.risk_flags, decision.missing_information

    def evidence(source: str, finding: str, reference: str) -> None:
        decision.evidence.append(EvidenceItem(source=source, finding=finding, reference=reference))

    def require(role: str, flag: str, reason: str, section: str) -> None:
        approvals.append(role)
        flags.append(flag)
        evidence("policy_rules", reason, "procurement_policy.md §" + section)

    for result in pack.tools:
        if not result.ok:
            flags.append("vendor_risk_unavailable" if result.name == "vendor_risk" else "tool_unavailable")
            missing.append(f"Verify {result.name} evidence manually ({result.error})")
            evidence(result.name, "Evidence unavailable; no favorable status inferred.", result.name)

    policy = pack.result("policy")
    if not policy.ok:
        approvals.extend(["Procurement", "Security"])
        flags.append("policy_unavailable")
        decision.recommendation = "Hold: policy unavailable"
        decision.next_step = "Procurement must restore the policy and rerun all checks before any approval."
        decision.human_review_required = True
        return decision
    reference = date.fromisoformat(policy.data["reference_date"])
    evidence("policy", f"Policy {policy.data['version']}; reference date {reference}; SHA256 {policy.data['sha256']}",
             "data/procurement_policy.md")

    identity = pack.result("requester_budget").data
    employee, budget = identity.get("employee"), identity.get("budget")
    if not employee:
        missing.append("Valid requester and department")
    else:
        evidence("requester_budget", f"Requester {employee['employee_id']}; department {employee['department']}; manager {employee['manager_id'] or 'unrecorded'}.", "employees.csv:" + employee["employee_id"])
        if req.get("department") and normal(req["department"]) != normal(employee["department"]):
            flags.append("department_mismatch")
            missing.append("Resolve requester department mismatch")
    for field, label in [("vendor_name", "Product/vendor"), ("product_name", "Product name"),
                         ("business_justification", "Business purpose")]:
        if not isinstance(req.get(field), str) or not req[field].strip():
            missing.append(label)
    cost = amount(req.get("annual_cost_usd"))
    if cost is None:
        missing.append("Valid annual cost estimate in USD")
    else:
        approvals.extend(business_approvals(cost))
        evidence("policy_rules", f"Annual amount ${cost:,.2f}; minimum approvals: {', '.join(business_approvals(cost))}.", "procurement_policy.md §4")
    seats = req.get("user_count")
    if type(seats) is not int or seats <= 0:
        missing.append("Positive integer user/license count")
    access = normal(req.get("data_access_level")).replace(" ", "_").replace("-", "_")
    if access not in KNOWN_ACCESS:
        missing.append("Known intended data access level")
    integrations = req.get("requested_integrations")
    if not isinstance(integrations, list) or any(not isinstance(i, str) or not i.strip() for i in integrations):
        missing.append("Required integrations (an empty list explicitly means none)")
        integrations = []

    available = amount(budget.get("available_usd")) if budget else None
    if available is None:
        missing.append("Verified department available budget")
        approvals.append("Finance")
    elif cost is not None:
        total, committed = amount(budget.get("annual_software_budget_usd")), amount(budget.get("committed_usd"))
        if total is None or committed is None or total - committed != available:
            flags.append("budget_conflicting")
            missing.append("Reconcile budget totals with Finance")
            approvals.append("Finance")
        evidence("requester_budget", f"{budget['department']}: available ${available:,.2f}; request ${cost:,.2f}; remaining if purchased ${available-cost:,.2f}.", "department_budgets.csv:" + budget["department"])
        if cost > available:
            require("Finance", "budget_insufficient", f"Budget shortfall ${cost-available:,.2f}; a budget exception is required.", "2")

    catalog = pack.result("catalog").data
    for item in catalog.get("matches", []):
        flags.append("existing_tool_overlap")
        evidence("catalog", f"{item['product_name']} ({item['category']}), {item['status']}; scope {item['scope']}; {item['licensed_seats']} total licensed seats. Spare capacity and use-case fit need validation.", "software_catalog.csv:" + item["software_id"])
    if pack.result("catalog").ok and not catalog.get("matches"):
        evidence("catalog", "No exact product/vendor/category match. Semantic fit still needs assessment.", "software_catalog.csv")
    for purchase in pack.result("history").data.get("purchases", []):
        evidence("history", f"Prior {purchase['status']} purchase of {purchase['product_name']} for {purchase['department']}: ${purchase['annual_amount_usd']:,.2f}. This does not authorize the requested use case.", "purchase_history.csv:" + purchase["purchase_id"])

    vendor = pack.result("registry").data.get("vendor")
    risk_result = pack.result("vendor_risk")
    risk = risk_result.data
    if vendor:
        evidence("registry", f"{vendor['vendor_name']}: procurement {vendor['procurement_status']}; security {vendor['security_status']}; review {vendor['security_review_date'] or 'missing'}; legal {vendor['legal_terms_status']}.", "vendors.csv:" + vendor["vendor_id"])
    else:
        missing.append("Internal vendor registry record/onboarding")
    if risk_result.ok:
        evidence("vendor_risk", f"{risk['vendor_name']}: risk {risk['risk_level']}; security {risk['security_review_status']}; review {risk['last_review_date'] or 'missing'}; personal-data capability {risk['processes_personal_data']}; outside-region storage {risk['stores_data_outside_region']}.", "/vendor-risk/" + str(req.get("vendor_name", "")))
    internal_state = review_state(vendor.get("security_status"), vendor.get("security_review_date"), reference) if vendor else "missing"
    external_state = review_state(risk.get("security_review_status"), risk.get("last_review_date"), reference) if risk_result.ok else "unavailable"
    if "expired" in (internal_state, external_state) or normal(risk.get("security_review_status")) == "expired":
        flags.append("vendor_review_expired")
        evidence("policy_rules", "At least one vendor review exceeds 365 days or is explicitly expired.", "procurement_policy.md §5")
    if vendor and risk_result.ok:
        # Pending and not_completed are equivalent; approved vs expired is a conflict even if both dates are stale.
        canonical = lambda s: "pending" if normal(s) in {"pending", "not_completed"} else normal(s)
        if canonical(vendor["security_status"]) != canonical(risk["security_review_status"]) or str(vendor["security_review_date"] or "") != str(risk["last_review_date"] or ""):
            flags.append("conflicting_vendor_evidence")
            evidence("policy_rules", "Internal registry and vendor-risk service disagree; Security must reconcile both sources.", "procurement_policy.md §5")
    sensitive = access in {"source_code", "production_telemetry", "confidential_documents", "employee_pii", "customer_pii", "credentials", "secrets"}
    integration_text = normal(" ".join(integrations))
    sensitive_integration = bool(re.search(r"\b(production|prod|cloud|aws|azure|gcp|git|github|gitlab|repository|repositories|credentials?)\b", integration_text))
    # Business purpose may reveal sensitive access omitted from the structured field.
    purpose = normal(req.get("business_justification"))
    sensitive_purpose = any(t in purpose for t in ("source code", "customer pii", "employee pii", "confidential", "credentials", "production access"))
    if sensitive or sensitive_integration or sensitive_purpose or access not in KNOWN_ACCESS or internal_state != "current" or external_state != "current" or "conflicting_vendor_evidence" in flags:
        require("Security", "security_review_required", f"Security must review data/integration scope and vendor assessment (internal {internal_state}, external {external_state}).", "5")
    pii = "pii" in access or any(t in purpose for t in ("customer pii", "employee pii", "personal data", "customer emails", "employee records"))
    cross_region = risk.get("stores_data_outside_region") is True and (sensitive or sensitive_purpose or pii or access not in KNOWN_ACCESS)
    if pii or cross_region:
        require("Privacy", "privacy_review_required", "PII processing or potentially sensitive data stored outside the operating region requires Privacy review.", "6")
    new_vendor = not vendor or normal(vendor["procurement_status"]) != "approved"
    nonstandard = not vendor or normal(vendor["legal_terms_status"]) not in {"approved", "standard"}
    if (new_vendor and cost is not None and cost >= 10000) or nonstandard or cross_region:
        require("Legal", "legal_review_required", "New-vendor spend, nonstandard/unverified terms, or a material cross-region data issue requires Legal review.", "7")
    if suspicious(json.dumps(req, default=str)) or any(suspicious(json.dumps(t.data, default=str)) for t in pack.tools if t.name != "policy"):
        flags.append("prompt_injection_detected")
        evidence("policy_rules", "Instruction-like content in business data was ignored; it cannot establish approval.", "procurement_policy.md §9")
    if missing:
        flags.append("missing_information")
        approvals.append("Procurement")
    if not risk_result.ok:
        approvals.append("Security")
    decision.required_approvals = list(dict.fromkeys(approvals))
    decision.risk_flags = list(dict.fromkeys(flags))
    decision.missing_information = list(dict.fromkeys(missing))
    if missing:
        decision.recommendation = "Request clarification / manual verification"
    elif "budget_insufficient" in flags:
        decision.recommendation = "Hold for budget exception and required reviews"
    elif any(r in approvals for r in ("Security", "Privacy", "Legal")):
        decision.recommendation = "Route for specialist and business reviews"
    elif "existing_tool_overlap" in flags:
        decision.recommendation = "Review existing agreement before new spend"
    else:
        decision.recommendation = "Route for business approval"
    steps = []
    if missing:
        steps.append("Clarify/verify: " + "; ".join(decision.missing_information) + ".")
    if "budget_insufficient" in flags:
        steps.append("Finance must resolve the budget shortfall before purchase.")
    if "existing_tool_overlap" in flags:
        steps.append("Validate existing license capacity, scope and the requested gap; overlap alone is not rejection.")
    steps.append("Send this evidence package to " + ", ".join(decision.required_approvals) + " for human review. Do not purchase until approvals are recorded outside this app.")
    decision.next_step = " ".join(steps)
    return decision
