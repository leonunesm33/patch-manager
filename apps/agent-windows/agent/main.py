import json
import os
import platform
import socket
import time
from urllib import error, request


API_BASE = os.getenv("PATCH_MANAGER_API", "http://localhost:8000/api/v1/agents")
AGENT_KEY = os.getenv("PATCH_MANAGER_AGENT_KEY", "patch-manager-agent-key")
AGENT_ID = os.getenv("PATCH_MANAGER_AGENT_ID", "windows-agent-01")
PLATFORM = "windows"
AGENT_VERSION = "0.1.0"


def post_json(path: str, payload: dict[str, object]) -> object | None:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{API_BASE}{path}",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-agent-key": AGENT_KEY,
        },
        method="POST",
    )
    with request.urlopen(req, timeout=10) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else None


def heartbeat() -> None:
    post_json(
        "/heartbeat",
        {
            "agent_id": AGENT_ID,
            "platform": PLATFORM,
            "hostname": socket.gethostname(),
        },
    )


def check_in() -> None:
    post_json(
        "/check-in",
        {
            "agent_id": AGENT_ID,
            "platform": PLATFORM,
            "hostname": socket.gethostname(),
            "os_name": platform.system(),
            "os_version": platform.version(),
            "kernel_version": platform.release(),
            "agent_version": AGENT_VERSION,
        },
    )


def claim_job() -> dict[str, object] | None:
    response = post_json(
        "/claim-job",
        {
            "agent_id": AGENT_ID,
            "platform": PLATFORM,
        },
    )
    return response if isinstance(response, dict) else None


def submit_result(job_id: str, result: str, error_message: str | None = None) -> None:
    post_json(
        f"/jobs/{job_id}/result",
        {
            "agent_id": AGENT_ID,
            "result": result,
            "error_message": error_message,
        },
    )


def main() -> None:
    print(f"Windows agent online: {AGENT_ID}")
    check_in()
    while True:
        try:
            heartbeat()
            job = claim_job()
            if job and job.get("id"):
                print(f"Processing job {job['id']} for patch {job['patch_id']}")
                time.sleep(2)
                submit_result(str(job["id"]), "applied")
            else:
                time.sleep(5)
        except error.URLError as exc:
            print(f"Agent connection failed: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    main()
