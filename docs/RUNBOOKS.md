# SRE runbooks

## Runbook: high CPU

1. Confirm alarm state, threshold, evaluation periods, and dimensions.
2. Compare average and maximum CPU over 1h and 24h.
3. Correlate with deployment events, traffic volume, throttling, and dependency latency.
4. Inspect application logs and traces around the alarm timestamp.
5. Determine whether saturation is expected load, leak, hot loop, bad deployment, or downstream retry amplification.
6. Recommend scale-out, rollback, traffic shaping, or code fix with impact/rollback.
7. Require approval before changing capacity or restarting workloads.
8. Verify CPU, latency, errors, and saturation after approved action.

## Runbook: elevated 5xx

1. Establish affected service, endpoint, region, and customer impact.
2. Compare 5xx rate with request volume and p95/p99 latency.
3. Inspect recent deployments and configuration changes.
4. Correlate application exceptions with dependency failures.
5. Check ALB target health, ECS/EKS pod readiness, Lambda errors/throttles, and database connections as applicable.
6. Recommend rollback or traffic shift only after evidence and approval.
7. Verify error rate returns to baseline.

## Runbook: EKS CrashLoopBackOff (extension)

- Inspect pod events, previous container logs, restart count, probes, OOMKilled state, resource limits, image pull, config/secret mounts, and node pressure.
- Do not print Kubernetes Secret values.
- Recommend `kubectl describe` / redacted logs as evidence; never execute arbitrary kubectl from an LLM-generated string.
- Any rollout restart or scaling operation must go through an approved executor.

## Runbook: agent itself is unhealthy

- Check Runtime status and invocation errors.
- Check Bedrock model access, throttling, quotas, and Region.
- Check IAM `AccessDenied` for model and CloudWatch actions.
- Check Logs Insights query duration/timeouts.
- Check concurrency, token budget, and model latency.
- Disable tool access if prompt injection or unsafe action behavior is suspected.
