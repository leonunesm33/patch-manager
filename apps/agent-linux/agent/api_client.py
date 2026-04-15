import json
from urllib import error
from urllib import request

from config import AgentConfig


def post_json(
    config: AgentConfig,
    path: str,
    payload: dict[str, object],
    extra_headers: dict[str, str] | None = None,
) -> object | None:
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "x-agent-id": config.agent_id,
    }
    if config.agent_key:
        headers["x-agent-key"] = config.agent_key
    if extra_headers:
        headers.update(extra_headers)
    req = request.Request(
        f"{config.api_base}{path}",
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=config.request_timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        setattr(exc, "response_json", json.loads(raw) if raw else {})
        raise


def post_optional_json(
    config: AgentConfig,
    path: str,
    payload: dict[str, object],
    extra_headers: dict[str, str] | None = None,
) -> object | None:
    return post_json(config, path, payload, extra_headers=extra_headers)
