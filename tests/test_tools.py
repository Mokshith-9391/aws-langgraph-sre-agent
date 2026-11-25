from sre_agent.tools import query_logs
from sre_agent.config import settings

def test_logs_prefix_guard(monkeypatch):
    monkeypatch.setattr(settings, "aws_allowed_log_group_prefixes", "/approved/")
    assert "allow-listed" in query_logs("/not-approved/app", "fields @message")["error"]
