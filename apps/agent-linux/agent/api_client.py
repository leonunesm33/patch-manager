import json
from urllib import request

from config import AgentConfig


def post_json(config: AgentConfig, path: str, payload: dict[str, object]) -> object | None:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        f"{config.api_base}{path}",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-agent-key": config.agent_key,
        },
        method="POST",
    )
    with request.urlopen(req, timeout=config.request_timeout_seconds) as response:
        raw = response.read().decode("utf-8")
        return json.loads(raw) if raw else None
