from __future__ import annotations

import json
import ssl
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


BASE_URL = "http://127.0.0.1:8000"
GATEWAY_URL = "https://127.0.0.1"
COMPOSE_DIR = Path("/home/leonardo/patch-manager/infra/compose")


@dataclass
class Result:
    name: str
    ok: bool
    detail: str


def request(
    method: str,
    url: str,
    body: dict[str, object] | None = None,
    token: str | None = None,
    *,
    insecure: bool = False,
    timeout: int = 15,
) -> tuple[int, object | None, str, str | None]:
    data = None
    headers = {"Accept": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    context = ssl._create_unverified_context() if insecure else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=context) as response:
            raw = response.read().decode("utf-8", "replace")
            parsed = None
            if "application/json" in response.headers.get("content-type", "") and raw:
                parsed = json.loads(raw)
            return response.status, parsed, raw, None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", "replace")
        return exc.code, None, raw, None
    except Exception as exc:  # noqa: BLE001 - smoke tests should capture every failure.
        return 0, None, "", str(exc)


def short(value: object) -> str:
    return str(value).replace("\n", " ")[:260]


def add(results: list[Result], name: str, ok: bool, detail: object) -> None:
    results.append(Result(name=name, ok=ok, detail=short(detail)))


def fallback_admin_token() -> str:
    return subprocess.check_output(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "api",
            "python",
            "-c",
            'from app.core.security import create_access_token; print(create_access_token("admin"))',
        ],
        cwd=COMPOSE_DIR,
        text=True,
    ).strip()


def main() -> int:
    results: list[Result] = []

    status, data, raw, err = request("GET", f"{BASE_URL}/health/detailed")
    add(
        results,
        "health detalhado API",
        status == 200 and isinstance(data, dict) and data.get("database") == "ok",
        data or err or raw,
    )

    status, _, raw, err = request("GET", GATEWAY_URL, insecure=True)
    add(results, "gateway HTTPS/frontend", status == 200, f"status={status} err={err or raw[:80]}")

    status, data, raw, err = request(
        "POST",
        f"{BASE_URL}/api/v1/auth/login",
        {"username": "admin", "password": "admin123"},
    )
    login_token = data.get("access_token") if status == 200 and isinstance(data, dict) else None
    add(results, "login admin/admin123", status == 200, data or raw or err)
    token = login_token or fallback_admin_token()

    protected_gets = [
        ("auth/me", "/api/v1/auth/me"),
        ("dashboard", "/api/v1/dashboard"),
        ("maquinas", "/api/v1/machines"),
        ("grupos maquinas", "/api/v1/machines/groups"),
        ("aprovacoes", "/api/v1/patches"),
        ("agendamentos", "/api/v1/schedules"),
        ("relatorios", "/api/v1/reports"),
        ("configuracoes", "/api/v1/settings"),
        ("usuarios", "/api/v1/users"),
        ("perfis usuarios", "/api/v1/users/roles"),
        ("agentes conectados", "/api/v1/agents/connected"),
        ("agentes pendentes", "/api/v1/agents/enrollments/pending"),
        ("agentes rejeitados", "/api/v1/agents/enrollments/rejected"),
        ("agentes revogados", "/api/v1/agents/revoked"),
        ("agentes parados", "/api/v1/agents/stopped"),
        ("snapshots inventario", "/api/v1/agents/inventory-snapshots"),
        ("comandos recentes", "/api/v1/agents/commands/recent"),
        ("jobs agentes", "/api/v1/agents/jobs"),
        ("scheduler status", "/api/v1/agents/scheduler-status"),
    ]
    for name, path in protected_gets:
        status, data, raw, err = request("GET", BASE_URL + path, token=token)
        count = len(data) if isinstance(data, list) else "obj" if isinstance(data, dict) else "-"
        add(results, name, 200 <= status < 300, f"status={status} count={count} err={err or raw[:120]}")

    status, machines, raw, err = request("GET", f"{BASE_URL}/api/v1/machines", token=token)
    if status == 200 and isinstance(machines, list) and machines:
        first_machine = machines[0]
        machine_id = urllib.parse.quote(str(first_machine["id"]), safe="")
        status, _, raw, err = request("GET", f"{BASE_URL}/api/v1/machines/{machine_id}", token=token)
        add(
            results,
            "detalhe maquina",
            status == 200,
            f"status={status} id={first_machine['id']} err={err or raw[:120]}",
        )
        status, _, raw, err = request(
            "GET",
            f"{BASE_URL}/api/v1/machines/{machine_id}/operational-details",
            token=token,
        )
        add(
            results,
            "detalhe operacional maquina",
            status == 200,
            f"status={status} id={first_machine['id']} err={err or raw[:120]}",
        )
        status, data, raw, err = request(
            "GET",
            f"{BASE_URL}/api/v1/patches?machine_id={machine_id}&approval_status=pending",
            token=token,
        )
        count = len(data) if isinstance(data, list) else "-"
        add(results, "filtro patches por maquina", status == 200, f"status={status} count={count} err={err or raw[:120]}")
    else:
        add(results, "detalhes maquina", False, f"sem maquinas status={status} err={err or raw[:120]}")

    installers = [
        (
            "instalador linux",
            "/api/v1/agents/install/linux.sh?server_url=http%3A%2F%2Flocalhost%3A8000&bootstrap_token=patch-manager-bootstrap-token",
            ["PATCH_MANAGER", "systemctl"],
        ),
        (
            "upgrade linux",
            "/api/v1/agents/install/linux-upgrade.sh?server_url=http%3A%2F%2Flocalhost%3A8000",
            ["pending_updates", "_collect_apt_upgradable_details"],
        ),
        (
            "instalador windows",
            "/api/v1/agents/install/windows.ps1?server_url=http%3A%2F%2Flocalhost%3A8000&bootstrap_token=patch-manager-bootstrap-token",
            ["PatchManagerAgentWindows", "Register-ScheduledTask"],
        ),
        (
            "upgrade windows",
            "/api/v1/agents/install/windows-upgrade.ps1?server_url=http%3A%2F%2Flocalhost%3A8000",
            ["PatchManagerAgentWindows", "Task reiniciada"],
        ),
    ]
    for name, path, markers in installers:
        status, _, raw, err = request("GET", BASE_URL + path, token=token)
        missing = [marker for marker in markers if marker not in raw]
        add(results, name, status == 200 and not missing, f"status={status} bytes={len(raw)} missing={missing} err={err}")

    for name, path in [
        ("processar fila jobs inicial", "/api/v1/agents/process-jobs"),
        ("run cycle patch", "/api/v1/agents/run-cycle"),
        ("processar fila jobs apos ciclo", "/api/v1/agents/process-jobs"),
    ]:
        status, data, raw, err = request("POST", BASE_URL + path, token=token)
        add(results, name, 200 <= status < 300, data or raw or err)

    test_group_name = "Smoke Test Group"
    status, group_data, raw, err = request(
        "POST",
        f"{BASE_URL}/api/v1/machines/groups",
        {"name": test_group_name, "description": "Grupo temporario criado pelo smoke test."},
        token=token,
    )
    group_id = group_data.get("id") if status == 201 and isinstance(group_data, dict) else None
    add(results, "criar grupo temporario", status in {201, 409}, group_data or raw or err)

    schedule_payload = {
        "name": "Smoke Test Schedule",
        "scope_type": "os",
        "scope_value": "Windows",
        "install_date": None,
        "install_time": "02:10",
        "reboot_date": None,
        "reboot_time": "03:10",
        "recurrence": "once",
        "reboot_policy": "if-needed",
    }
    status, schedule_data, raw, err = request(
        "POST",
        f"{BASE_URL}/api/v1/schedules",
        schedule_payload,
        token=token,
    )
    schedule_id = schedule_data.get("id") if status == 201 and isinstance(schedule_data, dict) else None
    add(results, "criar agendamento estruturado", status == 201, schedule_data or raw or err)

    if schedule_id:
        status, _, raw, err = request("DELETE", f"{BASE_URL}/api/v1/schedules/{schedule_id}", token=token)
        add(results, "remover agendamento estruturado", status == 204, f"status={status} err={err or raw[:120]}")

    if group_id:
        status, _, raw, err = request("DELETE", f"{BASE_URL}/api/v1/machines/groups/{group_id}", token=token)
        add(results, "remover grupo temporario", status == 204, f"status={status} err={err or raw[:120]}")

    print("SMOKE_RESULTS_BEGIN")
    for result in results:
        print(f"{'PASS' if result.ok else 'FAIL'}|{result.name}|{result.detail}")
    print("SMOKE_RESULTS_END")

    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
