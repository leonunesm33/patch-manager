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
from config import load_config, save_env_values
from executor import execute_windows_job, handle_post_apply_reboot
from inventory import collect_inventory
from logger import configure_logging


class EnrollmentRejectedError(RuntimeError):
    pass


def heartbeat(config) -> None:
    post_json(
        config,
        "/heartbeat",
        {
            "agent_id": config.agent_id,
            "platform": config.platform,
            "hostname": socket.gethostname(),
        },
    )


def check_in(config) -> None:
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


def send_inventory(config) -> None:
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


def claim_job(config) -> dict[str, object] | None:
    response = post_json(
        config,
        "/claim-job",
        {
            "agent_id": config.agent_id,
            "platform": config.platform,
        },
    )
    return response if isinstance(response, dict) else None


def submit_result(config, job_id: str, result: str, execution_mode: str, error_message: str | None = None) -> None:
    post_json(
        config,
        f"/jobs/{job_id}/result",
        {
            "agent_id": config.agent_id,
            "result": result,
            "execution_mode": execution_mode,
            "reboot_required": False,
            "error_message": error_message,
        },
    )


def enroll_agent(config, logger: logging.Logger):
    if not config.bootstrap_token:
        return config

    while True:
        inventory = collect_inventory(config.agent_version, config.default_execution_mode)
        response = post_json(
            config,
            "/enroll",
            {
                "agent_id": config.agent_id,
                "platform": config.platform,
                "hostname": inventory["hostname"],
                "primary_ip": inventory["primary_ip"],
                "os_name": inventory["os_name"],
                "os_version": inventory["os_version"],
                "kernel_version": inventory["kernel_version"],
                "agent_version": config.agent_version,
            },
            extra_headers={"x-bootstrap-token": config.bootstrap_token},
        )

        if isinstance(response, dict) and response.get("status") == "approved" and response.get("agent_key"):
            issued_key = str(response["agent_key"])
            save_env_values(
                config.env_file_path,
                {
                    "PATCH_MANAGER_AGENT_ID": config.agent_id,
                    "PATCH_MANAGER_AGENT_KEY": issued_key,
                },
            )
            config.agent_key = issued_key
            logger.info("Bootstrap enrollment approved for %s", config.agent_id)
            return config

        if isinstance(response, dict) and response.get("status") == "rejected":
            logger.error("Bootstrap enrollment rejected for %s", config.agent_id)
            raise EnrollmentRejectedError(config.agent_id)

        poll_seconds = int(response.get("poll_interval_seconds", 15)) if isinstance(response, dict) else 15
        logger.info("Enrollment pending approval for %s", config.agent_id)
        time.sleep(poll_seconds)


def revoke_agent_credential(config, logger: logging.Logger):
    if not config.bootstrap_token:
        raise SystemExit(1)

    save_env_values(config.env_file_path, {"PATCH_MANAGER_AGENT_KEY": ""})
    config.agent_key = ""
    logger.warning("Agent credential revoked. Returning to bootstrap enrollment.")
    return enroll_agent(config, logger)


def _sleep_until(stop_event: threading.Event, seconds: int) -> bool:
    return stop_event.wait(seconds)


def main() -> None:
    config = load_config()
    logger = configure_logging(config)
    stop_event = threading.Event()
    last_inventory_sync = 0.0
    last_heartbeat = 0.0

    logger.info("Windows agent online: %s", config.agent_id)
    logger.info("API base: %s", config.api_base)
    logger.info("Windows agent default mode: %s", config.default_execution_mode)

    try:
        if not config.agent_key and config.bootstrap_token:
            logger.info("No agent credential found. Starting bootstrap enrollment flow.")
            config = enroll_agent(config, logger)
        check_in(config)
        send_inventory(config)
        now = time.monotonic()
        last_inventory_sync = now
        last_heartbeat = now
    except EnrollmentRejectedError:
        logger.error("Agent enrollment was rejected. Stopping agent process.")
        raise SystemExit(0)
    except error.HTTPError as exc:
        if exc.code == 401 and config.bootstrap_token:
            try:
                config = revoke_agent_credential(config, logger)
                check_in(config)
                send_inventory(config)
                now = time.monotonic()
                last_inventory_sync = now
                last_heartbeat = now
            except EnrollmentRejectedError:
                logger.error("Agent enrollment was rejected. Stopping agent process.")
                raise SystemExit(0)
        else:
            logger.warning("Initial request failed with status %s", exc.code)
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
                result, error_message, reboot_required = execute_windows_job(job, job_mode, config)
                reboot_scheduled = False
                reboot_message = None
                if result == "applied" and reboot_required:
                    reboot_scheduled, reboot_message = handle_post_apply_reboot(job, reboot_required, config)
                _sleep_until(stop_event, 2)
                submit_result(
                    config,
                    str(job["id"]),
                    result,
                    job_mode,
                    reboot_required,
                    reboot_scheduled,
                    reboot_message,
                    error_message,
                )
                logger.info(
                    "Finished job %s with result %s%s%s",
                    job["id"],
                    result,
                    f" | reboot: {reboot_message}" if reboot_message else "",
                    f": {error_message}" if error_message else "",
                )
            else:
                _sleep_until(stop_event, config.idle_sleep_seconds)
        except error.HTTPError as exc:
            if exc.code == 401 and config.bootstrap_token:
                try:
                    config = revoke_agent_credential(config, logger)
                except EnrollmentRejectedError:
                    logger.error("Agent enrollment was rejected. Stopping agent process.")
                    stop_event.set()
            else:
                logger.warning("Agent request failed with status %s", exc.code)
                _sleep_until(stop_event, config.failure_backoff_seconds)
        except error.URLError as exc:
            logger.warning("Agent connection failed: %s", exc)
            _sleep_until(stop_event, config.failure_backoff_seconds)
        except KeyboardInterrupt:
            logger.info("Windows agent interrupted by operator.")
            stop_event.set()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected Windows agent failure: %s", exc)
            _sleep_until(stop_event, config.failure_backoff_seconds)

    logger.info("Windows agent stopped.")


if __name__ == "__main__":
    main()
