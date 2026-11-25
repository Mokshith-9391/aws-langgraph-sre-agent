import time
from sre_agent.approval import issue_demo_approval, validate_approval
from sre_agent.config import settings

def test_approval_rejects_expired_or_missing_secret(monkeypatch):
    monkeypatch.setattr(settings, "approval_hmac_secret", "unit-test-secret")
    expiry = int(time.time()) + 60
    token = issue_demo_approval("ecs:UpdateService:forceNewDeployment", "cluster/service", expiry)
    assert validate_approval(token, "ecs:UpdateService:forceNewDeployment", "cluster/service", expiry)
    assert not validate_approval(token, "ecs:UpdateService:forceNewDeployment", "other/service", expiry)
    assert not validate_approval(token, "ecs:UpdateService:forceNewDeployment", "cluster/service", int(time.time()) - 1)
