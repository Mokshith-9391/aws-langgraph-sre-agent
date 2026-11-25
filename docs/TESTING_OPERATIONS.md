# Testing and operations

## Test pyramid

- Unit: approval validation, input validation, log-group allow-list, parsing and severity mapping.
- Component: mocked boto3 CloudWatch clients and mocked Bedrock responses.
- Integration: non-production AWS account, approved log groups, known alarms/metrics.
- Evaluation: golden incident dataset with expected evidence, likely cause, severity, and safe actions.
- Security: prompt injection in logs, cross-tenant resource IDs, malformed dimensions, oversized queries, expired approval, replayed approval, and tool timeout.

## Operational metrics

Track:
- invocation count, success/error rate, p50/p95/p99 latency;
- model input/output tokens, model throttles, cost per incident;
- tool calls by type, failures, timeouts, and denied scope attempts;
- evidence completeness, diagnosis confidence, human override rate;
- approved action success, rollback rate, and time-to-mitigate.

## SLO examples

Define SLOs with your service owners. Example starting targets:
- 99.5% successful analysis invocations per 30-day window;
- p95 read-only triage completion under 60 seconds for bounded evidence queries;
- 100% of mutating actions require valid external approval;
- 0 unapproved production mutations.

These are example targets, not measured guarantees.

## CI/CD recommendations

- Run Ruff, mypy, pytest, dependency and container scans.
- Build immutable image tags.
- Generate SBOM and sign image.
- Use OIDC federation from CI to AWS; no static AWS keys.
- Require environment approvals for production.
- Deploy canary, run smoke tests, then promote.
- Keep last known-good image digest for rollback.

## Known scaffold limitations

- The graph is synchronous and uses an in-memory workflow invocation; durable cross-invocation checkpointing is not configured.
- AgentCore Memory, Gateway, Identity, Policy, and Evaluations are documented as extension points, not automatically provisioned by this Terraform foundation.
- Logs Insights query polling is bounded and returns a query ID if still running.
- The local FastAPI harness is for development, not the AgentCore production ingress.
- The demo approval helper is not a replacement for an enterprise change-management system.
