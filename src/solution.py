from __future__ import annotations

from src.contracts import Architecture, ProcurementDecision
from src.contracts import RunTelemetry
from src.data_access import get_request
from src.tools import gather
from src.rules import apply_rules
from src.telemetry import RunTelemetryCounter
from src.agents import ModelUnavailable, reason
import os


def handle_request(request_id: str, architecture: Architecture = "single") -> ProcurementDecision:
    """Assessment adapter.

    Keep this function callable by the public/hidden evaluation harness.
    Your internal implementation may use any framework, modules, agents, tools,
    deterministic checks, or orchestration strategy.
    """
    return analyze_request(get_request(request_id), architecture)


def analyze_request(request: dict, architecture: Architecture = "single", *,
                    mode: str | None = None) -> ProcurementDecision:
    if architecture not in {"single", "staged"}:
        raise ValueError("Architecture must be single or staged")
    mode = mode or os.getenv("COPILOT_MODE", "auto")
    if mode not in {"auto", "live", "offline"}:
        raise ValueError("COPILOT_MODE must be auto, live, or offline")
    telemetry = RunTelemetryCounter()
    pack = gather(dict(request), telemetry)
    telemetry.record_tool_call("policy_rules")
    decision = apply_rules(pack)
    decision.trace = [{"stage": "evidence", "tools": [t.model_dump() for t in pack.tools]},
                      {"stage": "deterministic_checks", "risk_flags": list(decision.risk_flags)}]
    if mode == "offline":
        decision.warnings.append("Rules-only run: model reasoning was disabled. This is not a live agent evaluation.")
    elif "policy_unavailable" not in decision.risk_flags:
        try:
            reason(pack, decision, architecture, telemetry)
        except ModelUnavailable as exc:
            if mode == "live":
                raise
            decision.warnings.append(str(exc) + "; showing rules-only manual handoff.")
            decision.risk_flags.append("model_unavailable")
    decision.telemetry = RunTelemetry(llm_calls=telemetry.llm_calls, tool_calls=telemetry.tool_calls,
                                      tool_names=telemetry.tool_names)
    decision.human_review_required = True
    return decision
