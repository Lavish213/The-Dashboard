import hmac
import os

from fastapi import Header, HTTPException


def verify_karpathys_secret(x_karpathys_secret: str = Header(default="")) -> None:
    secret = os.environ.get("KARPATHYS_WEBHOOK_SECRET", "")
    if not secret:
        raise HTTPException(status_code=503, detail="Webhook authentication is not configured")
    if not hmac.compare_digest(x_karpathys_secret.encode(), secret.encode()):
        raise HTTPException(status_code=401, detail="Invalid secret")
