"""Environment diagnostics for Agent2."""

from __future__ import annotations

import socket
import subprocess
from dataclasses import dataclass
from pathlib import Path
from shutil import which

import yaml

from shared.config import load_agent_config, load_framework_config


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str


def run_doctor(project_root: Path) -> list[CheckResult]:
    """Run local Agent2 diagnostics without mutating files."""

    results = [
        _binary_check("git"),
        _binary_check("docker"),
        _binary_check("uv"),
        _file_check(project_root / ".env", ".env"),
        _file_check(project_root / "agent2.yaml", "agent2.yaml"),
        _compose_check(project_root),
        _framework_config_check(project_root),
    ]
    results.extend(_agent_port_checks(project_root))
    return results


def _binary_check(binary: str) -> CheckResult:
    path = which(binary)
    return CheckResult(binary, bool(path), path or f"{binary} not found on PATH")


def _file_check(path: Path, label: str) -> CheckResult:
    return CheckResult(label, path.exists(), str(path) if path.exists() else f"{label} missing")


def _compose_check(project_root: Path) -> CheckResult:
    try:
        subprocess.run(
            ["docker", "compose", "config", "--quiet"],
            cwd=project_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return CheckResult("docker compose config", True, "valid")
    except Exception as exc:
        return CheckResult("docker compose config", False, str(exc))


def _framework_config_check(project_root: Path) -> CheckResult:
    try:
        config = load_framework_config(project_root / "agent2.yaml")
        model = config.default_model or "<env fallback>"
        return CheckResult("framework config", True, f"default_model={model}, stack={config.stack_profile}")
    except Exception as exc:
        return CheckResult("framework config", False, str(exc))


def _agent_port_checks(project_root: Path) -> list[CheckResult]:
    agents_dir = project_root / "agents"
    if not agents_dir.exists():
        return [CheckResult("agents", False, "agents directory missing")]

    results: list[CheckResult] = []
    used_ports: dict[int, str] = {}
    for config_path in sorted(agents_dir.glob("*/config.yaml")):
        if config_path.parent.name.startswith("_"):
            continue
        try:
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            name = str(data.get("name") or config_path.parent.name)
            config = load_agent_config(name)
            if config.port in used_ports:
                results.append(
                    CheckResult(
                        f"port {config.port}",
                        False,
                        f"used by {used_ports[config.port]} and {name}",
                    )
                )
            else:
                used_ports[config.port] = name
            if _port_is_open(config.port):
                results.append(CheckResult(f"{name} health port", True, f"localhost:{config.port} is open"))
        except Exception as exc:
            results.append(CheckResult(str(config_path), False, str(exc)))
    return results


def _port_is_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.1)
        return sock.connect_ex(("127.0.0.1", port)) == 0
