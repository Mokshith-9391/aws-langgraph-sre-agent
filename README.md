# Production AWS SRE Agent — LangGraph + Amazon Bedrock AgentCore

A production-oriented reference implementation for AWS incident investigation using LangGraph, Amazon Bedrock, and Amazon Bedrock AgentCore Runtime.

> **Safety boundary:** The included agent is read-only by default. It can inspect CloudWatch alarms, metrics, and logs, then produce a remediation plan. No production mutation is performed by default. The sample approval gate demonstrates a signed, short-lived approval token before a narrowly allow-listed action. Review and adapt IAM, policy, change-management, and approval controls before production use.

## What is included

- LangGraph state machine with triage, evidence collection, diagnosis, remediation planning, and response generation.
- Amazon Bedrock Converse integration through `ChatBedrockConverse`.
- Read-only CloudWatch tools: alarm description, metric query, and Logs Insights query.
- Explicit approval gate for remediation; sample action allow-list is intentionally small.
- AgentCore Runtime Python SDK entry point (`@app.entrypoint`) and `/ping` health support through the SDK.
- Docker image, ECR/IAM/CloudWatch/S3/DynamoDB Terraform foundation, deployment helper scripts.
- Unit tests, sample incident payloads, operational runbooks, security checklist, and CI workflow.
- Persistent conversation checkpointing is designed as an extension point; local development uses an in-memory checkpointer. For multi-replica production, use a supported durable LangGraph checkpointer (for example PostgreSQL) or AgentCore Memory, with encryption, TTL, and tenant isolation.

## Architecture

```text
Operator / Incident API
        |
        v
Amazon Bedrock AgentCore Runtime
        |
        v
LangGraph SRE workflow
  |-- classify incident
  |-- gather CloudWatch alarm/metric/log evidence
  |-- diagnose probable cause
  |-- propose remediation
  |-- require approval for mutation
  |-- verify and report
        |
        +---- Amazon Bedrock model (Converse API)
        +---- CloudWatch / Logs Insights (read-only)
        +---- optional AWS service-specific adapters
        |
        v
CloudWatch Logs + X-Ray/OpenTelemetry
```

## Prerequisites

- AWS account and an IAM identity permitted to deploy the resources.
- AWS CLI v2 configured (`aws configure` or an assumed role).
- Terraform >= 1.6.
- Docker with Buildx.
- Python 3.11+.
- Node.js >= 20.12 and AgentCore CLI (`npm install -g @aws/agentcore`) if using the CLI deployment route.
- Bedrock model access enabled in the target Region for the chosen model.
- Region where the required AgentCore Runtime and Bedrock model features are available.

## Quick start — local

```bash
cp .env.example .env
# Edit AWS_REGION, MODEL_ID, LOG_LEVEL and optional limits.
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
aws sts get-caller-identity
python -m sre_agent.main
```

In another terminal:

```bash
curl -sS http://localhost:8080/invocations \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "Investigate alarm HighCPU-Production on EC2 instance i-0123456789abcdef0",
    "session_id": "incident-2026-001"
  }'
```

The local server is a small compatibility harness for development. AgentCore production execution uses the SDK entry point in `src/sre_agent/agentcore_app.py`.

## Deploy to AWS

### 1. Configure variables

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Set project_name, aws_region, account-specific settings.
```

### 2. Provision foundation

```bash
cd terraform
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
cd ..
```

Terraform provisions an ECR repository, execution role and policies, CloudWatch log group, S3 evidence bucket, and DynamoDB incident/audit table. It intentionally does not claim to manage every AgentCore capability through a Terraform resource: the AgentCore Runtime is deployed with the supported AgentCore CLI in this reference. This split avoids relying on an unverified provider resource schema. You can replace the CLI step with AWS SDK/IaC resources once your selected provider version supports the exact AgentCore features you need.

### 3. Build and push container

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export ECR_REPOSITORY="$(terraform -chdir=terraform output -raw ecr_repository_name)"
export IMAGE_TAG="$(git rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)"

aws ecr get-login-password --region "$AWS_REGION" | \
  docker login --username AWS --password-stdin \
  "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker buildx build --platform linux/arm64 \
  -t "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:$IMAGE_TAG" \
  --push .
```

### 4. Deploy AgentCore Runtime

Install the AgentCore CLI and authenticate using the same AWS account/Region. Follow the current CLI workflow:

```bash
npm install -g @aws/agentcore
agentcore --help
```

Create a Runtime project using the current CLI template, then configure it to use this project's container image and entry point. CLI options and project configuration evolve; consult the official AgentCore CLI guide linked below rather than copying stale flags.

For direct container deployment, use the AgentCore Runtime deployment interface documented for your account/Region and provide:
- ECR image URI from Terraform output and build step.
- Execution role ARN from `terraform output agent_execution_role_arn`.
- Environment variables: `AWS_REGION`, `MODEL_ID`, `LOG_LEVEL`, `MAX_LOG_EVENTS`, `LOG_LOOKBACK_MINUTES`.
- Container port `8080` and entry module `sre_agent.agentcore_app:app` as required by the chosen packaging/CLI template.

**Important:** AgentCore Runtime requires its documented runtime contract. This project uses `BedrockAgentCoreApp` and `@app.entrypoint`; validate the packaging and deployment command against the current AgentCore CLI/SDK release before deploying.

### 5. Invoke

Use AgentCore CLI `agentcore invoke` or the AWS SDK `bedrock-agentcore` Runtime client as documented for your SDK version. Example payload:

```json
{
  "prompt": "Investigate the elevated 5xx rate for checkout-api",
  "session_id": "inc-2026-001",
  "context": {
    "alarm_name": "Checkout5xxHigh",
    "log_group": "/aws/ecs/checkout-api"
  }
}
```

### 6. Verify

- Confirm Runtime health and invocation logs.
- Confirm Bedrock model invocation succeeds in the target Region.
- Confirm CloudWatch read-only tools are restricted to approved resources.
- Run `pytest`.
- Run the test incident payload in `examples/incident_payload.json`.
- Verify that an unapproved remediation request only returns a proposal and never mutates infrastructure.

## Request contract

```json
{
  "prompt": "Investigate the alarm",
  "session_id": "incident-123",
  "context": {
    "alarm_name": "HighCPU",
    "namespace": "AWS/EC2",
    "metric_name": "CPUUtilization",
    "dimensions": {"InstanceId": "i-0123456789abcdef0"},
    "log_group": "/aws/my-app"
  }
}
```

Optional `approval_token` is accepted only for the explicit allow-listed remediation demonstration. Never expose signing secrets to users or agent prompts. Replace the sample HMAC flow with an authenticated approval service / change-management integration in production.

## Project structure

```text
.
├── src/sre_agent/
│   ├── agentcore_app.py    # AgentCore SDK entry point
│   ├── config.py           # Typed environment configuration
│   ├── graph.py            # LangGraph workflow
│   ├── llm.py              # Bedrock model factory
│   ├── state.py            # Graph state schema
│   ├── tools.py            # Read-only AWS tools + guarded action
│   ├── approval.py         # HMAC approval token validation
│   └── main.py             # Local HTTP development harness
├── terraform/              # AWS foundation
├── scripts/                # build/deploy/test helpers
├── tests/                  # unit tests
├── docs/                   # deployment, security, runbooks
├── Dockerfile
└── pyproject.toml
```

## Production hardening before go-live

1. Replace broad resource wildcards with exact account/Region/resource ARNs.
2. Use IAM roles and short-lived credentials; never place AWS keys in `.env`, images, or Terraform state.
3. Put Runtime behind the required private networking controls where applicable; restrict egress.
4. Use AgentCore Identity/Gateway/Policy where external tools and delegated identities are required.
5. Add durable checkpointing, session ownership checks, retention/TTL, and tenant isolation.
6. Add an authenticated human approval service; enforce change windows, blast-radius limits, idempotency, and rollback.
7. Add CloudWatch dashboards, alarms, structured traces, SLOs, DLQs for asynchronous work, and incident correlation IDs.
8. Evaluate model/tool behavior with curated incident datasets; block deployment on regression.
9. Apply Bedrock model invocation quotas, token budgets, timeouts, retries with jitter, and concurrency limits.
10. Run threat modeling, penetration testing, IAM Access Analyzer, and disaster-recovery exercises.

## Documentation

- [End-to-end deployment guide](docs/DEPLOYMENT_GUIDE.md)
- [Architecture and workflow](docs/ARCHITECTURE.md)
- [Security and guardrails](docs/SECURITY.md)
- [SRE runbooks](docs/RUNBOOKS.md)
- [Testing and operations](docs/TESTING_OPERATIONS.md)

## Official references

- Amazon Bedrock AgentCore Developer Guide: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/
- AgentCore Runtime Python direct deployment: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-get-started-code-deploy-python.html
- AgentCore framework integration / LangGraph: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/using-any-agent-framework.html
- AgentCore CLI tutorial: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-cli-get-started.html
- LangGraph documentation: https://docs.langchain.com/oss/python/langgraph/overview
# aws-langgraph-sre-agent
