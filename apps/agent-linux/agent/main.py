import logging
import os
import platform
import socket
import threading
import sys
import time
from urllib import error

CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from api_client import post_json
from config import AgentConfig, load_config
from executor import execute_patch_job_with_mode
from inventory import collect_inventory
from logger import configure_logging


def heartbeat(config: AgentConfig) -> None:
    post_json(
        config,
        "/heartbeat",
        {
            "agent_id": config.agent_id,
            "platform": config.platform,
            "hostname": socket.gethostname(),
        },
    )


def check_in(config: AgentConfig) -> None:
    post_json(
        config,
        "/check-in",
        {
            "agent_id": config.agent_id,
            "platform": config.platform,
            "hostname": socket.gethostname(),
            "os_name": platform.system(),
            "os_version": platform.version(),
            "kernel_version": platform.release(),
            "agent_version": config.agent_version,
            "execution_mode": config.default_execution_mode,
        },
    )


def send_inventory(config: AgentConfig) -> None:
    inventory = collect_inventory(config.agent_version, config.default_execution_mode)
    post_json(
        config,
        "/inventory",
        {
            "agent_id": config.agent_id,
            "platform": config.platform,
            **inventory,
        },
    )


def claim_job(config: AgentConfig) -> dict[str, object] | None:
    response = post_json(
        config,
        "/claim-job",
        {
            "agent_id": config.agent_id,
            "platform": config.platform,
        },
    )
    return response if isinstance(response, dict) else None


def submit_result(
    config: AgentConfig,
    job_id: str,
    result: str,
    error_message: str | None = None,
) -> None:
    post_json(
        config,
        f"/jobs/{job_id}/result",
        {
            "agent_id": config.agent_id,
            "result": result,
            "error_message": error_message,
        },
    )


def _sleep_until(stop_event: threading.Event, seconds: int) -> bool:
    return stop_event.wait(seconds)


def main() -> None:
    config = load_config()
    logger = configure_logging(config)
    stop_event = threading.Event()
    last_inventory_sync = 0.0
    last_heartbeat = 0.0

    logger.info("Linux agent online: %s", config.agent_id)
    logger.info("API base: %s", config.api_base)
    logger.info("Linux agent default mode: %s", config.default_execution_mode)

    try:
        check_in(config)
        send_inventory(config)
        now = time.monotonic()
        last_inventory_sync = now
        last_heartbeat = now
    except error.URLError as exc:
        logger.warning("Initial connection failed: %s", exc)

    while not stop_event.is_set():
        try:
            now = time.monotonic()
            if now - last_heartbeat >= config.heartbeat_interval_seconds:
                heartbeat(config)
                last_heartbeat = now

            if now - last_inventory_sync >= config.inventory_interval_seconds:
                send_inventory(config)
                last_inventory_sync = now

            job = claim_job(config)
            if job and job.get("id"):
                job_mode = str(job.get("execution_mode", config.default_execution_mode))
                logger.info(
                    "Processing job %s for patch %s in mode %s",
                    job["id"],
                    job["patch_id"],
                    job_mode,
                )
                result, error_message = execute_patch_job_with_mode(job, job_mode)
                _sleep_until(stop_event, 2)
                submit_result(config, str(job["id"]), result, error_message)
                logger.info(
                    "Finished job %s with result %s%s",
                    job["id"],
                    result,
                    f": {error_message}" if error_message else "",
                )
            else:
                _sleep_until(stop_event, config.idle_sleep_seconds)
        except error.URLError as exc:
            logger.warning("Agent connection failed: %s", exc)
            _sleep_until(stop_event, config.failure_backoff_seconds)
        except KeyboardInterrupt:
            logger.info("Linux agent interrupted by operator.")
            stop_event.set()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected agent failure: %s", exc)
            _sleep_until(stop_event, config.failure_backoff_seconds)

    logger.info("Linux agent stopped.")


if __name__ == "__main__":
    main()
