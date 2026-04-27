"""LearnerLLM protocol and ConfiguredLearnerLLM implementation."""
from __future__ import annotations

import json
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class LearnerLLM(Protocol):
    """Protocol for LLM backends used by the auto-learning pipeline."""

    def extract(
        self,
        prompt: str,
        system: str | None = None,
        timeout: float = 30.0,
    ) -> dict | None:
        """Extract rule candidate. Returns None on timeout or failure (never raises)."""
        ...


def _resolve_agent_learner_home() -> Path:
    override = os.environ.get("AGENT_LEARNER_HOME", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".agent-learner").resolve()


def _load_llm_config(project_root: Path) -> dict:
    """Load LLM config with priority: project > global > defaults."""
    defaults: dict = {"provider": "anthropic", "model": "claude-sonnet-4-6", "endpoint": None}

    # Project config
    project_config_path = project_root / ".agent-learner" / "config.json"
    if project_config_path.exists():
        try:
            payload = json.loads(project_config_path.read_text(encoding="utf-8"))
            if "llm" in payload:
                defaults.update(payload["llm"])
                return defaults
        except (json.JSONDecodeError, OSError):
            pass

    # Global config
    global_config_path = _resolve_agent_learner_home() / "config.json"
    if global_config_path.exists():
        try:
            payload = json.loads(global_config_path.read_text(encoding="utf-8"))
            if "llm" in payload:
                defaults.update(payload["llm"])
                return defaults
        except (json.JSONDecodeError, OSError):
            pass

    return defaults


class ConfiguredLearnerLLM:
    """LLM backend that reads config from project/global config.json."""

    def __init__(self, project_root: Path) -> None:
        config = _load_llm_config(project_root)
        self.provider: str = config["provider"]
        self.model: str = config["model"]
        self.endpoint: str | None = config.get("endpoint")

    def extract(
        self,
        prompt: str,
        system: str | None = None,
        timeout: float = 30.0,
    ) -> dict | None:
        """Extract with timeout enforcement. Returns None on failure."""
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self._call_api, prompt, system)
                return future.result(timeout=timeout)
        except FuturesTimeoutError:
            return None
        except Exception:
            return None

    def _call_api(self, prompt: str, system: str | None = None) -> dict | None:
        """Override in subclasses or monkeypatch for real API calls."""
        raise NotImplementedError("Subclasses must implement _call_api")
