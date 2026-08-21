import logging
import os
import platform
import shlex
import socket
import subprocess
import threading
import sys
import time
import urllib.parse
from urllib import error

CURRENT_DIR = os.path.dirname(__file__)
if CURRENT_DIR not in sys.path:
    sys.path.append(CURRENT_DIR)

from api_client import post_json
from config import AgentConfig, load_config, save_env_values
from executor import execute_manual_reboot_command, execute_patch_job_with_mode, handle_post_apply_reboot
from inventory import collect_inventory
from logger import configure_logging


class EnrollmentRejectedError(RuntimeError):
    pass


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


def poll_command(config: AgentConfig) -> dict[str, object] | None:
    response = post_json(
        config,
        "/commands/next",
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
    execution_mode: str,
    reboot_required: bool | None,
    reboot_scheduled: bool | None,
    reboot_message: str | None,
    error_message: str | None = None,
) -> None:
    post_json(
        config,
        f"/jobs/{job_id}/result",
        {
            "agent_id": config.agent_id,
            "result": result,
            "execution_mode": execution_mode,
            "reboot_required": reboot_required,
            "reboot_scheduled": reboot_scheduled,
            "reboot_message": reboot_message,
            "error_message": error_message,
        },
    )


def submit_command_result(
    config: AgentConfig,
    command_id: str,
    result: str,
    message: str | None = None,
) -> None:
    post_json(
        config,
        f"/commands/{command_id}/result",
        {
            "agent_id": config.agent_id,
            "result": result,
            "message": message,
        },
    )


def enroll_agent(config: AgentConfig, logger: logging.Logger) -> AgentConfig:
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
            logger.info("Bootstrap enrollment approved for agent %s", config.agent_id)
            return config

        if isinstance(response, dict) and response.get("status") == "rejected":
            logger.error("Bootstrap enrollment rejected for agent %s", config.agent_id)
            raise EnrollmentRejectedError(config.agent_id)

        poll_seconds = 15
        if isinstance(response, dict):
            poll_seconds = int(response.get("poll_interval_seconds", 15))
        logger.info("Enrollment pending approval for agent %s", config.agent_id)
        time.sleep(poll_seconds)


def revoke_agent_credential(config: AgentConfig, logger: logging.Logger) -> AgentConfig:
    if not config.bootstrap_token:
        logger.error("Agent credential revoked and no bootstrap token is configured.")
        raise SystemExit(1)

    save_env_values(
        config.env_file_path,
        {
            "PATCH_MANAGER_AGENT_KEY": "",
        },
    )
    config.agent_key = ""
    logger.warning("Agent credential revoked. Returning to bootstrap enrollment.")
    return enroll_agent(config, logger)


def _sleep_until(stop_event: threading.Event, seconds: int) -> bool:
    return stop_event.wait(seconds)


def _schedule_force_reidentify(
    command: dict[str, object],
    config: AgentConfig,
) -> tuple[str, str]:
    payload = command.get("payload")
    if not isinstance(payload, dict):
        return "failed", "Payload de reidentificacao ausente ou invalido."

    server_url = str(payload.get("server_url") or "").strip().rstrip("/")
    bootstrap_token = str(payload.get("bootstrap_token") or "").strip()
    new_agent_id = str(payload.get("new_agent_id") or "").strip()
    parsed = urllib.parse.urlparse(server_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "failed", "server_url de reidentificacao invalida."
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        return "failed", "Reidentificacao remota exige HTTPS fora de localhost."
    if not bootstrap_token:
        return "failed", "bootstrap_token de reidentificacao ausente."
    if not new_agent_id.startswith("linux-") or not all(
        character.isalnum() or character == "-" for character in new_agent_id
    ):
        return "failed", "new_agent_id Linux invalido."

    query = urllib.parse.urlencode(
        {
            "server_url": server_url,
            "bootstrap_token": bootstrap_token,
            "agent_id": new_agent_id,
        }
    )
    installer_url = f"{server_url}/api/v1/agents/install/linux.sh?{query}"
    subprocess.Popen(
        [
            "bash",
            "-c",
            f"sleep 3 && curl -fsSL {shlex.quote(installer_url)} | sudo bash",
        ],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return (
        "applied",
        f"Reidentificacao agendada como {new_agent_id}; o servico sera reiniciado.",
    )


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
        if not config.agent_key and config.bootstrap_token:
            logger.info("No agent credential found. Starting bootstrap enrollment flow.")
            config = enroll_agent(config, logger)
    except EnrollmentRejectedError:
        logger.error("Agent enrollment was rejected. Stopping agent process.")
        raise SystemExit(0)

    try:
        check_in(config)
        send_inventory(config)
        now = time.monotonic()
        last_inventory_sync = now
        last_heartbeat = now
    except error.HTTPError as exc:
        if exc.code == 401 and config.bootstrap_token:
            try:
                config = revoke_agent_credential(config, logger)
            except EnrollmentRejectedError:
                logger.error("Agent enrollment was rejected. Stopping agent process.")
                raise SystemExit(0)
        else:
            logger.warning("Initial agent request failed with status %s", exc.code)
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

            command = poll_command(config)
            if command and command.get("id"):
                command_type = str(command.get("command_type", "")).strip().lower()
                logger.info("Processing command %s of type %s", command["id"], command_type)
                if command_type == "upgrade_agent":
                    submit_command_result(config, str(command["id"]), "applied", "Upgrade do agente iniciado.")
                    _parsed = urllib.parse.urlparse(config.api_base)
                    server_url = f"{_parsed.scheme}://{_parsed.netloc}"
                    encoded_url = urllib.parse.quote(server_url, safe="")
                    upgrade_url = f"{server_url}/api/v1/agents/install/linux-upgrade.sh?server_url={encoded_url}"
                    subprocess.Popen(
                        ["bash", "-c", f'sleep 3 && curl -fsSL "{upgrade_url}" | sudo bash'],
                        start_new_session=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    logger.info("Upgrade script scheduled for agent %s", config.agent_id)
                elif command_type == "force_reidentify":
                    result, message = _schedule_force_reidentify(command, config)
                    submit_command_result(config, str(command["id"]), result, message)
                    logger.warning(
                        "Force reidentification command %s finished scheduling with result %s: %s",
                        command["id"],
                        result,
                        message,
                    )
                elif command_type in {"reboot_now", "scheduled_reboot"}:
                    result, message = execute_manual_reboot_command(command, config)
                    submit_command_result(config, str(command["id"]), result, message)
                    logger.info(
                        "Finished command %s with result %s%s",
                        command["id"],
                        result,
                        f" | {message}" if message else "",
                    )
                else:
                    message = f"Tipo de comando nao suportado: {command_type or '<vazio>'}."
                    submit_command_result(config, str(command["id"]), "failed", message)
                    logger.error(message)
                continue

            job = claim_job(config)
            if job and job.get("id"):
                job_mode = str(job.get("execution_mode", config.default_execution_mode))
                logger.info(
                    "Processing job %s for patch %s in mode %s",
                    job["id"],
                    job["patch_id"],
                    job_mode,
                )
                result, error_message, reboot_required = execute_patch_job_with_mode(job, job_mode, config)
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
            logger.info("Linux agent interrupted by operator.")
            stop_event.set()
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected agent failure: %s", exc)
            _sleep_until(stop_event, config.failure_backoff_seconds)

    logger.info("Linux agent stopped.")


if __name__ == "__main__":
    main()
