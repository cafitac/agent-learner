from __future__ import annotations

import importlib.util
import socket
import shutil
import subprocess
import sys
from pathlib import Path

from .fastapi_app import app_root_dir, bundled_frontend_dist_dir, frontend_build_output_dir, frontend_dist_dir, frontend_dist_is_valid
from .storage import ensure_global_learning_root, resolve_learning_root


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def is_port_available(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


def frontend_root_dir(project_root: Path) -> Path:
    return app_root_dir() / "frontend"


def sync_bundled_frontend_dist() -> Path:
    source = frontend_build_output_dir()
    target = bundled_frontend_dist_dir()
    if not (source / "index.html").exists():
        raise RuntimeError("frontend build output was not found under frontend/dist")
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(source, target)
    return target


def collect_dashboard_doctor(project_root: Path, *, host: str = "127.0.0.1", port: int = 8766) -> dict[str, object]:
    project_root = project_root.resolve()
    frontend_root = frontend_root_dir(project_root)
    frontend_dist = frontend_dist_dir()
    node_modules = frontend_root / "node_modules"
    port_ok = is_port_available(host, port)
    dist_index_ok = (frontend_dist / "index.html").exists()
    dist_valid = frontend_dist_is_valid(frontend_dist) if dist_index_ok else False
    payload = {
        "project_root": str(project_root),
        "python": {"ok": True, "detail": sys.executable},
        "uv": {"ok": shutil.which("uv") is not None, "detail": shutil.which("uv") or ""},
        "node": {"ok": shutil.which("node") is not None, "detail": shutil.which("node") or ""},
        "npm": {"ok": shutil.which("npm") is not None, "detail": shutil.which("npm") or ""},
        "fastapi": {"ok": module_available("fastapi"), "detail": "import fastapi"},
        "uvicorn": {"ok": module_available("uvicorn"), "detail": "import uvicorn"},
        "frontend": {
            "root": str(frontend_root),
            "bundled_root": str(bundled_frontend_dist_dir()),
            "package_json": (frontend_root / "package.json").exists(),
            "node_modules": node_modules.exists(),
            "dist": frontend_dist.exists(),
            "dist_index": dist_index_ok,
            "dist_valid": dist_valid,
        },
        "brains": {
            "local_learning_root": str(resolve_learning_root(project_root)),
            "global_learning_root": str(ensure_global_learning_root()),
        },
        "port": {"host": host, "port": port, "ok": port_ok},
    }
    payload["ready_fastapi"] = bool(
        payload["fastapi"]["ok"]
        and payload["uvicorn"]["ok"]
        and payload["frontend"]["dist_valid"]
    )
    payload["ready_static"] = bool(payload["frontend"]["dist_valid"])
    payload["can_auto_build"] = bool(
        payload["node"]["ok"]
        and payload["npm"]["ok"]
        and payload["frontend"]["package_json"]
    )
    remediations: list[str] = []
    if not payload["uv"]["ok"]:
        remediations.append("Install uv for the recommended Python workflow.")
    if not payload["node"]["ok"] or not payload["npm"]["ok"]:
        remediations.append("Install Node.js and npm to build the React dashboard.")
    if not payload["fastapi"]["ok"] or not payload["uvicorn"]["ok"]:
        remediations.append("Run `uv sync --extra web` or install `agent-learner[web]`.")
    if not payload["frontend"]["node_modules"]:
        remediations.append("Run `cd frontend && npm install`.")
    if not payload["frontend"]["dist_index"]:
        remediations.append("Run `agent-learner dashboard --project-root <repo> --build` or `cd frontend && npm run build`.")
    elif not payload["frontend"]["dist_valid"]:
        remediations.append("Frontend dist exists but is invalid; rebuild with `cd frontend && npm run build`.")
    if not payload["port"]["ok"]:
        remediations.append(f"Port {port} is busy; use `agent-learner dashboard --port {port + 1}` or free the port.")
    if payload["ready_fastapi"] and payload["port"]["ok"]:
        status = "ready"
        verdict = "READY"
        next_command = "agent-learner dashboard --project-root <repo>"
        recommended_path = "fastapi"
    elif payload["ready_fastapi"] and not payload["port"]["ok"]:
        status = "blocked_port"
        verdict = "BLOCKED_PORT"
        next_command = f"agent-learner dashboard --project-root <repo> --port {port + 1}"
        recommended_path = "fastapi"
    else:
        status = "setup_required"
        verdict = "NEEDS_BUILD" if payload["node"]["ok"] and payload["npm"]["ok"] else "SETUP_REQUIRED"
        next_command = "uv sync --extra web && cd frontend && npm install && npm run build"
        recommended_path = "fastapi"
    payload["status"] = status
    payload["verdict"] = verdict
    payload["can_run_now"] = bool(payload["ready_fastapi"] and payload["port"]["ok"])
    payload["recommended_path"] = recommended_path
    payload["remediations"] = remediations
    payload["next_command"] = next_command
    return payload


def format_doctor_text(report: dict[str, object]) -> str:
    frontend = report["frontend"]
    lines = [
        f"verdict={report['verdict']}",
        f"status={report['status']}",
        f"project_root={report['project_root']}",
        f"python: ok ({report['python']['detail']})",
        f"uv: {'ok' if report['uv']['ok'] else 'missing'}",
        f"node: {'ok' if report['node']['ok'] else 'missing'}",
        f"npm: {'ok' if report['npm']['ok'] else 'missing'}",
        f"fastapi: {'ok' if report['fastapi']['ok'] else 'missing'}",
        f"uvicorn: {'ok' if report['uvicorn']['ok'] else 'missing'}",
        f"frontend package.json: {'ok' if frontend['package_json'] else 'missing'}",
        f"frontend node_modules: {'ok' if frontend['node_modules'] else 'missing'}",
        f"frontend dist: {'ok' if frontend['dist_index'] else 'missing'}",
        f"frontend dist valid: {'ok' if frontend['dist_valid'] else 'invalid'}",
        f"port {report['port']['host']}:{report['port']['port']}: {'ok' if report['port']['ok'] else 'busy'}",
        f"ready_fastapi={report['ready_fastapi']}",
        f"ready_static={report['ready_static']}",
        f"can_auto_build={report['can_auto_build']}",
        f"can_run_now={report['can_run_now']}",
        f"recommended_path={report['recommended_path']}",
    ]
    if report["remediations"]:
        lines.append("remediations:")
        lines.extend(f"- {item}" for item in report["remediations"])
    lines.append(f"next: {report['next_command']}")
    return "\n".join(lines)


def ensure_frontend_dist(project_root: Path, *, build: bool = False) -> Path:
    project_root = project_root.resolve()
    frontend_root = frontend_root_dir(project_root)
    dist = frontend_dist_dir()
    if (dist / "index.html").exists() and frontend_dist_is_valid(dist):
        return dist
    if not build:
        raise RuntimeError(
            "Built frontend dist was not found. Run `agent-learner dashboard --project-root <repo> --build` "
            "or manually `cd frontend && npm install && npm run build`."
        )
    if not shutil.which("npm"):
        raise RuntimeError("npm is not installed; cannot build frontend automatically.")
    if not (frontend_root / "node_modules").exists():
        subprocess.run(["npm", "install"], cwd=str(frontend_root), check=True)
    subprocess.run(["npm", "run", "build"], cwd=str(frontend_root), check=True)
    synced = sync_bundled_frontend_dist()
    if not (synced / "index.html").exists():
        raise RuntimeError("frontend build completed without producing bundled frontend_dist/index.html")
    return synced
