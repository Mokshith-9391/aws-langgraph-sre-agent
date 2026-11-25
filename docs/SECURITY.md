# Security, IAM, and agent guardrails

## Threat model

Protect against prompt injection in logs, malicious resource names, data exfiltration, unauthorized remediation, cross-account access, runaway loops, and compromised build/deploy pipelines.

## Non-negotiable controls

- Read-only investigation by default.
- Never allow the LLM to construct arbitrary boto3 calls, shell commands, or IAM policies.
- Treat log contents, tags, alarm descriptions, and ticket text as untrusted data, not instructions.
- Validate account, Region, resource ARN, log group, and tenant scope before every tool call.
- Use exact IAM resource ARNs and condition keys wherever supported.
- Require authenticated human approval outside the LLM before any production mutation.
- Enforce action allow-list, change window, blast-radius cap, idempotency key, timeout, and rollback plan.
- Separate investigation role from remediation executor role.
- Keep credentials in IAM role credentials / Secrets Manager; never in prompts, source, Docker layers, or logs.
- Encrypt data at rest and in transit; define retention and deletion.
- Redact PII, tokens, secrets, and customer payloads from evidence.

## IAM policy notes

The Terraform policy is a starting point, not a final production policy. CloudWatch Logs resource-level authorization differs by action; validate each action/resource combination against AWS IAM documentation. Bedrock model access should be limited to the exact foundation-model or inference-profile ARN used. The example policy intentionally omits production write permissions for EC2, EKS, ECS, Lambda, and Auto Scaling.

## Approval pattern

The sample HMAC validator is a demonstration only. HMAC signing secret distribution and approval issuance are not implemented as a user-facing approval system. Production flow should be:

1. Agent submits a structured proposed action to an approval API.
2. API authenticates the approver (SSO/MFA), checks RBAC and change policy.
3. API issues a one-time, short-lived, signed approval bound to action + resource + parameters + incident ID.
4. Dedicated executor validates signature, expiration, nonce, scope, and idempotency.
5. Executor logs approver identity, request, result, and rollback.
6. Agent verifies outcome read-only and reports status.

## Network

For private workloads, configure AgentCore Runtime VPC connectivity as supported by the selected service/Region, private endpoints where available, egress restrictions, DNS, and security groups. Do not assume the sample Docker image alone creates private networking.

## Data handling

Do not place raw production logs or customer data in model context without data classification, minimization, masking, and retention approval. Set bounded log query windows and result limits. Keep a separate evidence store with encryption and lifecycle policies if required.
