from langgraph.graph import StateGraph, START, END
from .state import SREState
from .llm import get_llm
from .tools import describe_alarm, get_metric_statistics, query_logs

SYSTEM = """You are a cautious senior AWS Site Reliability Engineer.
Use supplied evidence only; distinguish facts from hypotheses. Never claim an action was
executed unless action_result confirms it. Prefer reversible, low-blast-radius actions.
Never ask for or reveal credentials. Do not invent metrics, log lines, resource IDs, or causes.
Return concise incident analysis with severity, evidence, confidence, next checks and rollback."""

def classify(state: SREState) -> SREState:
    prompt = state.get("prompt", "")
    llm = get_llm()
    msg = llm.invoke([
        ("system", SYSTEM + " Classify severity as SEV1, SEV2, SEV3, or SEV4 and explain briefly."),
        ("human", prompt),
    ])
    text = str(msg.content)
    severity = next((s for s in ("SEV1", "SEV2", "SEV3", "SEV4") if s in text.upper()), "SEV3")
    return {"severity": severity, "evidence": state.get("evidence", []), "errors": state.get("errors", [])}

def collect_evidence(state: SREState) -> SREState:
    ctx = state.get("context", {})
    evidence = list(state.get("evidence", []))
    alarm_name = ctx.get("alarm_name")
    if alarm_name:
        evidence.append({"type": "cloudwatch_alarm", "data": describe_alarm(alarm_name)})
    metric = ctx.get("metric_name")
    if metric and ctx.get("namespace"):
        evidence.append({
            "type": "cloudwatch_metric",
            "data": get_metric_statistics(
                ctx["namespace"], metric, ctx.get("dimensions", {}),
                minutes=int(ctx.get("lookback_minutes", 60)),
            ),
        })
    if ctx.get("log_group") and ctx.get("logs_query"):
        evidence.append({
            "type": "cloudwatch_logs",
            "data": query_logs(ctx["log_group"], ctx["logs_query"]),
        })
    return {"evidence": evidence}

def diagnose(state: SREState) -> SREState:
    llm = get_llm()
    msg = llm.invoke([
        ("system", SYSTEM + " Diagnose likely causes. Clearly label confidence and missing evidence."),
        ("human", f"Incident: {state.get('prompt')}\\nSeverity: {state.get('severity')}\\nEvidence: {state.get('evidence', [])}"),
    ])
    return {"diagnosis": str(msg.content)}

def plan(state: SREState) -> SREState:
    llm = get_llm()
    msg = llm.invoke([
        ("system", SYSTEM + " Propose up to 3 remediation steps as JSON objects with action, rationale, risk, validation, rollback. Do not execute them."),
        ("human", f"Incident: {state.get('prompt')}\\nDiagnosis: {state.get('diagnosis')}"),
    ])
    return {"remediation_plan": [{"proposal": str(msg.content), "requires_human_approval": True}]}

def respond(state: SREState) -> SREState:
    llm = get_llm()
    msg = llm.invoke([
        ("system", SYSTEM + " Produce an incident report: summary, severity, evidence, likely root cause, recommended actions, approval status, verification, and next steps."),
        ("human", f"Prompt: {state.get('prompt')}\\nSeverity: {state.get('severity')}\\nEvidence: {state.get('evidence', [])}\\nDiagnosis: {state.get('diagnosis')}\\nPlan: {state.get('remediation_plan')}\\nAction result: {state.get('action_result')}"),
    ])
    return {"final_response": str(msg.content)}

def build_graph():
    graph = StateGraph(SREState)
    graph.add_node("classify", classify)
    graph.add_node("collect_evidence", collect_evidence)
    graph.add_node("diagnose", diagnose)
    graph.add_node("plan", plan)
    graph.add_node("respond", respond)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", "collect_evidence")
    graph.add_edge("collect_evidence", "diagnose")
    graph.add_edge("diagnose", "plan")
    graph.add_edge("plan", "respond")
    graph.add_edge("respond", END)
    return graph.compile()

sre_graph = build_graph()

def run_incident(payload: dict) -> dict:
    result = sre_graph.invoke({
        "prompt": payload.get("prompt", ""),
        "session_id": payload.get("session_id", "default"),
        "context": payload.get("context", {}),
        "approval_token": payload.get("approval_token", ""),
        "evidence": [],
        "errors": [],
    })
    return {
        "session_id": payload.get("session_id", "default"),
        "severity": result.get("severity"),
        "evidence": result.get("evidence", []),
        "diagnosis": result.get("diagnosis"),
        "remediation_plan": result.get("remediation_plan", []),
        "report": result.get("final_response"),
        "action_result": result.get("action_result"),
    }
