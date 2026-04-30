import secrets
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter
from fastapi.requests import Request

router = APIRouter(prefix="/mock/slurm", tags=["mock-slurm"])

@router.post("/submit")
async def submit(req: Request) -> dict[str, Any]:
    body = await req.json()
    return {
        "job_id":      f"mock-{secrets.token_hex(3)}",
        "status":      "accepted",
        "received_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "echo":        body,
    }
