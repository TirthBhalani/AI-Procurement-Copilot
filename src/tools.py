"""Read-only procurement tools. Failures are evidence, never approval."""
from __future__ import annotations

import hashlib
import re
from typing import Any, Callable

from pydantic import BaseModel, Field

from src import data_access as data
from src.telemetry import RunTelemetryCounter
from src.vendor_client import get_vendor_risk
from src.security import scrub


class ToolResult(BaseModel):
    name: str
    ok: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class EvidencePack(BaseModel):
    request: dict[str, Any]
    tools: list[ToolResult]

    def result(self, name: str) -> ToolResult:
        return next(t for t in self.tools if t.name == name)


def records(loader: Callable) -> list[dict]:
    return loader().fillna("").to_dict(orient="records")


def normal(value: object) -> str:
    return str(value or "").strip().casefold()


def requester_budget(request: dict) -> dict:
    employee = next((e for e in records(data.load_employees)
                     if e["employee_id"] == request.get("requester_id")), None)
    budget = next((b for b in records(data.load_budgets)
                   if employee and b["department"] == employee["department"]), None)
    return {"employee": employee, "budget": budget}


def catalog(request: dict) -> dict:
    approved = [r for r in records(data.load_software_catalog)
                if normal(r["status"]).startswith("approved")]
    matches = [r for r in approved if
               normal(r["vendor_name"]) == normal(request.get("vendor_name")) or
               normal(r["product_name"]) == normal(request.get("product_name")) or
               (normal(request.get("category")) and
                normal(r["category"]) == normal(request.get("category")))]
    return {"matches": matches, "approved_catalog": approved,
            "capacity_note": "Licensed seats are total entitlements; free seats are not recorded."}


def registry(request: dict) -> dict:
    return {"vendor": next((v for v in records(data.load_vendors)
                            if normal(v["vendor_name"]) == normal(request.get("vendor_name"))), None)}


def history(request: dict) -> dict:
    return {"purchases": [p for p in records(data.load_purchase_history)
                          if normal(p["vendor_name"]) == normal(request.get("vendor_name"))]}


def vendor_risk(request: dict) -> dict:
    if not request.get("vendor_name"):
        raise ValueError("Vendor is missing")
    payload = get_vendor_risk(request["vendor_name"])
    if normal(payload.get("vendor_name")) != normal(request["vendor_name"]):
        raise ValueError("Vendor identity mismatch")
    required = {"security_review_status", "last_review_date", "risk_level",
                "processes_personal_data", "stores_data_outside_region"}
    if not required.issubset(payload):
        raise ValueError("Incomplete vendor-risk response")
    for field in ("processes_personal_data", "stores_data_outside_region"):
        if type(payload[field]) is not bool:
            raise ValueError("Invalid vendor-risk boolean")
    return payload


def policy(_: dict) -> dict:
    text = data.load_policy_text()
    reference = re.search(r"reference date:\*\*\s*(\d{4}-\d{2}-\d{2})", text)
    version = re.search(r"\*\*Policy version:\*\*\s*(\S+)", text)
    if not reference:
        raise ValueError("Policy reference date is missing")
    if not version or version.group(1) != "2026.09":
        raise ValueError("Policy version needs a reviewed rules update")
    return {"text": text, "reference_date": reference.group(1),
            "sha256": hashlib.sha256(text.encode()).hexdigest(), "version": version.group(1)}


TOOLS = {"requester_budget": requester_budget, "catalog": catalog,
         "registry": registry, "history": history, "vendor_risk": vendor_risk,
         "policy": policy}


def gather(request: dict, telemetry: RunTelemetryCounter) -> EvidencePack:
    results = []
    for name, tool in TOOLS.items():
        telemetry.record_tool_call(name)
        try:
            results.append(ToolResult(name=name, ok=True, data=scrub(tool(request))))
        except Exception as exc:
            # Do not log URLs, response bodies, environment values, or credentials.
            results.append(ToolResult(name=name, ok=False, error=type(exc).__name__))
    return EvidencePack(request=request, tools=results)
