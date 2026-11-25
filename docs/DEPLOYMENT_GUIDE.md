# End-to-end deployment guide

## Phase 0 — choose Region and model

1. Choose an AWS Region supported by both AgentCore Runtime and your intended Bedrock model.
2. Confirm model/inference-profile availability and account access.
3. Confirm service quotas, model throughput, and AgentCore limits.
4. Set the same Region consistently for Terraform, ECR, Runtime, and Bedrock unless cross-Region inference is intentionally configured.

## Phase 1 — workstation setup

```bash
aws --version
terraform version
docker version
python --version
node --version
aws sts get-caller-identity
```

Use AWS IAM Identity Center or role assumption rather than long-lived IAM user keys. Ensure the deployment identity can provision ECR, IAM, S3, DynamoDB, CloudWatch, and AgentCore Runtime resources.

## Phase 2 — local install and test

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
pytest -q
python -m sre_agent.main
```

Test `/ping` and `/invocations`. For a real AWS test, configure an approved CloudWatch log group and an alarm/metric that exists in your account.

## Phase 3 — Terraform foundation

```bash
cp terraform/terraform.tfvars.example terraform/terraform.tfvars
# Edit exact model and log group ARNs.
terraform -chdir=terraform init
terraform -chdir=terraform fmt -check
terraform -chdir=terraform validate
terraform -chdir=terraform plan -out=tfplan
terraform -chdir=terraform apply tfplan
```

Inspect the IAM role policy. The sample variables default to broad values to make the scaffold understandable; replace them with exact resource ARNs before production. Consider separate roles for deployment and runtime.

## Phase 4 — build image

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPOSITORY=$(terraform -chdir=terraform output -raw ecr_repository_name)
export ECR_URI=$(terraform -chdir=terraform output -raw ecr_repository_url)
export IMAGE_TAG=$(git rev-parse --short HEAD)

aws ecr get-login-password --region "$AWS_REGION" | docker login \
  --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

docker buildx build --platform linux/arm64 -t "$ECR_URI:$IMAGE_TAG" --push .
```

Use immutable image tags and scan results. Pin base images by digest in regulated environments.

## Phase 5 — deploy Runtime

AgentCore deployment interfaces and CLI commands evolve. Use the current official guide:
https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/agentcore-cli-get-started.html

Typical CLI setup:
```bash
npm install -g @aws/agentcore
agentcore --help
```

Use the current CLI scaffold/configuration for a Python container agent. Point it to the image URI, runtime execution role, Region, and environment variables. The agent entry point is `src/sre_agent/agentcore_app.py` with `app` as the SDK application object. Ensure the final image meets the Runtime container contract and architecture requirements documented for your selected deployment method.

Runtime environment:
- `AWS_REGION`
- `MODEL_ID`
- `LOG_LEVEL`
- `MAX_LOG_EVENTS`
- `LOG_LOOKBACK_MINUTES`
- `AWS_ALLOWED_LOG_GROUP_PREFIXES`

Inject `APPROVAL_HMAC_SECRET` from Secrets Manager only if you retain the demo approval mechanism. Prefer a separate approval service and do not let the model generate or retrieve approval secrets.

## Phase 6 — test deployed invocation

Use the AgentCore CLI invocation workflow or AWS SDK Runtime client for your installed SDK version. Invoke with `examples/incident_payload.json`. Confirm:
- request accepted and response includes severity/report;
- CloudWatch calls use the intended account/Region;
- log group allow-list blocks unapproved groups;
- no write action occurs from a normal investigation request;
- Runtime logs and traces are available.

## Phase 7 — operational rollout

1. Start in a non-production AWS account.
2. Run read-only shadow mode against historical incidents.
3. Have SREs score root-cause quality and evidence accuracy.
4. Add approval workflow and narrow remediation executor.
5. Canary to one service/team.
6. Expand only after SLOs, cost, and safety gates pass.

## Rollback

- Stop invoking the Runtime or route traffic to the previous version.
- Redeploy the previous immutable image.
- Revoke the runtime role's write permissions immediately if unsafe behavior is observed.
- Preserve audit logs and incident evidence according to retention policy.
- Use Terraform state and change history to restore infrastructure changes; do not blindly destroy shared resources.
