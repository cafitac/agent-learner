from __future__ import annotations

import json
from pathlib import Path

from agent_learner import __version__

from .brain import apply_candidate_action, promote_rule_to_global
from .dashboard import build_dashboard_summary
from .storage import read_project_registry


def app_root_dir() -> Path:
    return Path(__file__).resolve().parents[3]


def package_root_dir() -> Path:
    return Path(__file__).resolve().parents[1]


def bundled_frontend_dist_dir() -> Path:
    return package_root_dir() / "frontend_dist"


def frontend_build_output_dir() -> Path:
    return app_root_dir() / "frontend" / "dist"


def frontend_dist_dir() -> Path:
    bundled = bundled_frontend_dist_dir()
    if bundled.exists():
        return bundled
    return frontend_build_output_dir()


def frontend_src_dir() -> Path:
    return app_root_dir() / "frontend" / "src"


def create_fastapi_app(project_root: Path):
    try:
        from fastapi import FastAPI, HTTPException
        from fastapi.responses import HTMLResponse, JSONResponse
        from fastapi.staticfiles import StaticFiles
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency gate
        raise RuntimeError("FastAPI extras are not installed. Install with `pip install .[web]` or `uv sync --extra web`.") from exc

    project_root = project_root.resolve()
    app = FastAPI(title="agent-learner dashboard", version=__version__)
    dist_dir = frontend_dist_dir()
    if not dist_dir.exists():
        raise RuntimeError(
            "Built frontend dist was not found. Run `cd frontend && npm install && npm run build` before `serve-dashboard-fastapi`."
        )

    @app.get("/api/projects")
    def get_projects() -> JSONResponse:
        return JSONResponse(read_project_registry())

    @app.get("/api/summary")
    def get_summary(project: str | None = None) -> JSONResponse:
        target_root = Path(project).resolve() if project else project_root
        return JSONResponse(build_dashboard_summary(target_root))

    @app.post("/api/promote-global")
    async def post_promote_global(payload: dict[str, object]) -> JSONResponse:
        name = str(payload.get("name") or "")
        if not name:
            raise HTTPException(status_code=400, detail="missing rule name")
        return JSONResponse(promote_rule_to_global(project_root, name, all_projects=bool(payload.get("all_projects", False))))

    @app.post("/api/review-candidate")
    async def post_review_candidate(payload: dict[str, object]) -> JSONResponse:
        candidate = str(payload.get("candidate") or "")
        action = str(payload.get("action") or "")
        if not candidate or action not in {"approve", "reject", "needs-review"}:
            raise HTTPException(status_code=400, detail="invalid candidate action payload")
        return JSONResponse(apply_candidate_action(project_root, candidate, action, reason=str(payload.get("reason") or "") or None))

    app.mount("/assets", StaticFiles(directory=dist_dir / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_spa(full_path: str = "") -> HTMLResponse:
        index_path = dist_dir / "index.html"
        return HTMLResponse(index_path.read_text(encoding="utf-8"))

    return app
