from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00', 'Z')


@dataclass(slots=True)
class LearningEvent:
    adapter: str
    event_name: str
    cwd: str
    captured_at: str
    session_id: str | None = None
    transcript_path: str | None = None
    payload: dict[str, object] = field(default_factory=dict)


def build_learning_event(
    *,
    adapter: str,
    event_name: str,
    cwd: str,
    session_id: str | None = None,
    transcript_path: str | None = None,
    payload: dict[str, object] | None = None,
) -> LearningEvent:
    return LearningEvent(
        adapter=adapter,
        event_name=event_name,
        cwd=cwd,
        captured_at=utc_now_iso(),
        session_id=session_id,
        transcript_path=transcript_path,
        payload=payload or {},
    )


def event_storage_dir(project_root: Path, adapter: str) -> Path:
    return project_root / '.agent-learner' / 'events' / adapter


def write_learning_event(project_root: Path, event: LearningEvent) -> Path:
    target_dir = event_storage_dir(project_root, event.adapter)
    target_dir.mkdir(parents=True, exist_ok=True)
    session_slug = (event.session_id or event.captured_at).replace('/', '-').replace(':', '-')
    target = target_dir / f"{event.event_name}-{session_slug}.json"
    target.write_text(json.dumps(asdict(event), ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return target
