import json
from datetime import datetime, timedelta, timezone
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from .config import settings
from .approval import validate_approval

def _client(service: str):
    return boto3.client(service, region_name=settings.aws_region)

def describe_alarm(alarm_name: str) -> dict:
    """Read-only: describe a CloudWatch metric alarm by exact name."""
    try:
        result = _client("cloudwatch").describe_alarms(AlarmNames=[alarm_name])
        alarms = result.get("MetricAlarms", [])
        return {"alarms": alarms, "count": len(alarms)}
    except (BotoCoreError, ClientError) as exc:
        return {"error": str(exc), "tool": "describe_alarm"}

def get_metric_statistics(namespace: str, metric_name: str, dimensions: dict,
                          minutes: int = 60, period: int = 300) -> dict:
    """Read-only CloudWatch metric query. Dimensions are exact key/value pairs."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=max(5, min(minutes, 1440)))
    dims = [{"Name": k, "Value": v} for k, v in dimensions.items()]
    try:
        result = _client("cloudwatch").get_metric_statistics(
            Namespace=namespace, MetricName=metric_name, Dimensions=dims,
            StartTime=start, EndTime=end, Period=max(60, period),
            Statistics=["Average", "Maximum", "Minimum"],
        )
        return {"datapoints": result.get("Datapoints", []), "label": result.get("Label")}
    except (BotoCoreError, ClientError) as exc:
        return {"error": str(exc), "tool": "get_metric_statistics"}

def query_logs(log_group: str, query: str, lookback_minutes: int | None = None) -> dict:
    """Read-only Logs Insights query with log-group prefix and time-window guardrails."""
    if not any(log_group.startswith(prefix) for prefix in settings.allowed_log_prefixes):
        return {"error": "log group is outside configured allow-listed prefixes"}
    # Only permit read-only Insights query language; reject mutation/control patterns.
    forbidden = ["delete", "update", "put", "create", "drop", "alter"]
    if any(word in query.lower().split() for word in forbidden):
        return {"error": "query contains a disallowed operation"}
    minutes = lookback_minutes or settings.log_lookback_minutes
    end = int(datetime.now(timezone.utc).timestamp())
    start = end - max(5, min(minutes, 1440)) * 60
    try:
        logs = _client("logs")
        started = logs.start_query(
            logGroupName=log_group, startTime=start, endTime=end,
            queryString=query, limit=max(1, min(settings.max_log_events, 500)),
        )
        query_id = started["queryId"]
        # Polling is deliberately bounded. For production, move this to async job orchestration.
        import time
        for _ in range(10):
            result = logs.get_query_results(queryId=query_id)
            if result.get("status") in {"Complete", "Failed", "Cancelled", "Timeout"}:
                return {"status": result.get("status"), "results": result.get("results", [])}
            time.sleep(1)
        return {"status": "Running", "query_id": query_id, "message": "Poll query_id asynchronously"}
    except (BotoCoreError, ClientError) as exc:
        return {"error": str(exc), "tool": "query_logs"}

def guarded_restart_ecs_service(cluster: str, service: str, approval_token: str,
                                expires_at: int, dry_run: bool = True) -> dict:
    """Demonstration action: only restart an ECS service after valid signed approval.

    Keep dry_run=True by default. Production should call a dedicated change-management
    executor with resource-level policy, idempotency, and rollback controls.
    """
    resource_id = f"{cluster}/{service}"
    if not validate_approval(approval_token, "ecs:UpdateService:forceNewDeployment", resource_id, expires_at):
        return {"status": "blocked", "reason": "valid unexpired approval required"}
    if dry_run:
        return {"status": "dry_run", "planned_action": "forceNewDeployment", "resource": resource_id}
    try:
        response = _client("ecs").update_service(
            cluster=cluster, service=service, forceNewDeployment=True
        )
        return {"status": "submitted", "service": response.get("service", {}).get("serviceName")}
    except (BotoCoreError, ClientError) as exc:
        return {"status": "error", "message": str(exc)}

def evidence_as_json(data: dict) -> str:
    return json.dumps(data, default=str)
