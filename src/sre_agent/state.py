from typing import Any, TypedDict

class SREState(TypedDict, total=False):
    prompt: str
    session_id: str
    context: dict[str, Any]
    evidence: list[dict[str, Any]]
    severity: str
    diagnosis: str
    remediation_plan: list[dict[str, Any]]
    approval_token: str
    action_result: dict[str, Any]
    final_response: str
    errors: list[str]
