import subprocess


def _run(command: list[str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return completed.returncode, (completed.stdout or completed.stderr).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)


def _derive_package_name(patch_id: str) -> str:
    for separator in ("=", "_", ":"):
        if separator in patch_id:
            return patch_id.split(separator, 1)[0]
    parts = patch_id.split("-")
    return parts[0] if parts else patch_id


def execute_patch_job(job: dict[str, object]) -> tuple[str, str | None]:
    return execute_patch_job_with_mode(job, "dry-run")


def execute_patch_job_with_mode(
    job: dict[str, object],
    execution_mode: str,
) -> tuple[str, str | None]:
    patch_id = str(job.get("patch_id", ""))
    package_name = _derive_package_name(patch_id)
    normalized_mode = execution_mode.strip().lower()

    if normalized_mode == "apply":
        code, output = _run(["apt-get", "-s", "install", "-y", package_name])
        if code == 0:
            return "applied", None
        return "failed", output or f"Unable to simulate install for package {package_name}"

    code, output = _run(["apt-cache", "policy", package_name])
    if code == 0 and output:
        return "applied", None
    return "failed", output or f"Unable to inspect package {package_name}"
