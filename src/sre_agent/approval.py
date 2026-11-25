import hashlib
import hmac
import time
from .config import settings

def issue_demo_approval(action: str, resource_id: str, expires_at: int) -> str:
    """Helper for tests/demo only. Production approvals must come from an authenticated approver."""
    message = f"{action}|{resource_id}|{expires_at}".encode()
    return hmac.new(settings.approval_hmac_secret.encode(), message, hashlib.sha256).hexdigest()

def validate_approval(token: str, action: str, resource_id: str, expires_at: int) -> bool:
    if not settings.approval_hmac_secret or not token or expires_at < int(time.time()):
        return False
    expected = issue_demo_approval(action, resource_id, expires_at)
    return hmac.compare_digest(token, expected)
