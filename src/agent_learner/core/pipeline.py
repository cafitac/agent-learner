from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from .events import LearningEvent, event_storage_dir

RULE_HINT_RE = re.compile(
    r"\b(always|never|prefer|must|should|do not|don't|keep|avoid|ensure|whenever)\b",
    re.IGNORECASE,
)
TEXT_VALUE_KEYS = {
    "prompt",
    "user_prompt",
    "message",
    "text",
    "summary",
    "feedback",
    "instruction",
    "content",
}


@dataclass(slots=True)
class LearningCandidate:
    adapter: str
    source_event_path: str
    captured_at: str
    title: str
    summary: str
    suggested_rule: str
    scope: str
    evidence_excerpt: str
    transcript_path: str | None = None


@dataclass(slots=True)
class ProcessedEventResult:
    event_path: str
    status: str
    candidate_path: str | None = None
    reason: str | None = None


def candidate_storage_dir(project_root: Path, adapter: str) -> Path:
    return project_root / ".agent-learner" / "candidates" / adapter


def processed_marker_dir(project_root: Path, processor: str, adapter: str) -> Path:
    return project_root / ".agent-learner" / "state" / "processed-events" / processor / adapter


def list_event_paths(project_root: Path, adapter: str | None = None) -> list[Path]:
    adapters = [adapter] if adapter else [path.name for path in (project_root / ".agent-learner" / "events").glob("*") if path.is_dir()]
    paths: list[Path] = []
    for adapter_name in adapters:
        paths.extend(sorted(event_storage_dir(project_root, adapter_name).glob("*.json")))
    return sorted(paths)


def load_learning_event(event_path: Path) -> LearningEvent:
    payload = json.loads(event_path.read_text(encoding="utf-8"))
    return LearningEvent(
        adapter=str(payload["adapter"]),
        event_name=str(payload["event_name"]),
        cwd=str(payload["cwd"]),
        captured_at=str(payload["captured_at"]),
        session_id=payload.get("session_id"),
        transcript_path=payload.get("transcript_path"),
        payload=dict(payload.get("payload") or {}),
    )


def is_processed(project_root: Path, event_path: Path, processor: str = "extract") -> bool:
    marker = processed_marker_dir(project_root, processor, event_path.parent.name) / f"{event_path.stem}.done"
    return marker.exists()


def mark_processed(project_root: Path, event_path: Path, processor: str = "extract") -> Path:
    marker = processed_marker_dir(project_root, processor, event_path.parent.name) / f"{event_path.stem}.done"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(event_path.name + "\n", encoding="utf-8")
    return marker


def process_unprocessed_events(project_root: Path, adapter: str | None = None, limit: int | None = None) -> list[ProcessedEventResult]:
    results: list[ProcessedEventResult] = []
    for event_path in list_event_paths(project_root, adapter=adapter):
        if limit is not None and len(results) >= limit:
            break
        if is_processed(project_root, event_path):
            continue
        event = load_learning_event(event_path)
        candidate = extract_candidate_from_event(project_root, event_path, event)
        candidate_path: Path | None = None
        if candidate is not None:
            candidate_path = write_candidate(project_root, candidate)
            status = "candidate_written"
        else:
            status = "no_candidate"
        mark_processed(project_root, event_path)
        results.append(
            ProcessedEventResult(
                event_path=str(event_path),
                status=status,
                candidate_path=str(candidate_path) if candidate_path else None,
                reason=None if candidate is not None else "no durable rule-like signal found",
            )
        )
    return results


def extract_candidate_from_event(project_root: Path, event_path: Path, event: LearningEvent) -> LearningCandidate | None:
    corpus = build_event_corpus(project_root, event)
    if not corpus.strip():
        return None
    evidence = find_rule_like_excerpt(corpus)
    if not evidence:
        return None
    title = build_candidate_title(event, evidence)
    summary = compact_text(evidence, 160)
    suggested_rule = normalize_rule_text(evidence)
    return LearningCandidate(
        adapter=event.adapter,
        source_event_path=str(event_path),
        captured_at=event.captured_at,
        title=title,
        summary=summary,
        suggested_rule=suggested_rule,
        scope=f"{event.adapter} adapter event:{event.event_name}",
        evidence_excerpt=compact_text(evidence, 260),
        transcript_path=event.transcript_path,
    )


def write_candidate(project_root: Path, candidate: LearningCandidate) -> Path:
    target_dir = candidate_storage_dir(project_root, candidate.adapter)
    target_dir.mkdir(parents=True, exist_ok=True)
    slug = slugify(candidate.title)
    target = target_dir / f"candidate-{slug}.md"
    body = [
        "---",
        f"adapter: {candidate.adapter}",
        f"captured_at: {candidate.captured_at}",
        f"source_event_path: {candidate.source_event_path}",
        f"transcript_path: {candidate.transcript_path or ''}",
        "status: draft_candidate",
        "---",
        "",
        f"# {candidate.title}",
        "",
        "## Suggested rule",
        candidate.suggested_rule,
        "",
        "## Summary",
        candidate.summary,
        "",
        "## Scope",
        candidate.scope,
        "",
        "## Evidence",
        candidate.evidence_excerpt,
        "",
    ]
    target.write_text("\n".join(body), encoding="utf-8")
    return target


def build_event_corpus(project_root: Path, event: LearningEvent) -> str:
    parts: list[str] = []
    parts.extend(extract_text_values(event.payload))
    transcript_path = resolve_transcript_path(project_root, event)
    if transcript_path and transcript_path.exists():
        parts.append(read_transcript_text(transcript_path))
    return "\n".join(part for part in parts if part.strip())


def resolve_transcript_path(project_root: Path, event: LearningEvent) -> Path | None:
    if not event.transcript_path:
        return None
    transcript = Path(event.transcript_path)
    if transcript.is_absolute():
        return transcript
    return project_root / transcript


def extract_text_values(payload: dict[str, object]) -> list[str]:
    values: list[str] = []
    for key, value in payload.items():
        if isinstance(value, str) and (key in TEXT_VALUE_KEYS or len(value.split()) > 3):
            values.append(value)
        elif isinstance(value, dict):
            values.extend(extract_text_values(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and len(item.split()) > 3:
                    values.append(item)
                elif isinstance(item, dict):
                    values.extend(extract_text_values(item))
    return values


def read_transcript_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    if path.suffix == ".jsonl":
        lines: list[str] = []
        for line in raw.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                lines.append(stripped)
                continue
            if isinstance(payload, dict):
                lines.extend(extract_text_values(payload))
        return "\n".join(lines)
    return raw


def find_rule_like_excerpt(corpus: str) -> str | None:
    for chunk in split_corpus(corpus):
        if RULE_HINT_RE.search(chunk):
            return chunk
    return None


def split_corpus(corpus: str) -> list[str]:
    normalized = corpus.replace("\r", "\n")
    pieces = re.split(r"[\n.!?]+", normalized)
    return [compact_text(piece, 260) for piece in pieces if piece.strip()]


def compact_text(text: str, limit: int) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else normalized[: limit - 3].rstrip() + "..."


def normalize_rule_text(text: str) -> str:
    cleaned = compact_text(text, 180)
    if cleaned and cleaned[-1] not in ".!?":
        cleaned += "."
    return cleaned[:1].upper() + cleaned[1:] if cleaned else cleaned


def build_candidate_title(event: LearningEvent, evidence: str) -> str:
    core = evidence.lower()
    for prefix in ["always ", "never ", "prefer ", "must ", "should ", "do not ", "don't ", "keep ", "avoid ", "ensure ", "whenever "]:
        if core.startswith(prefix):
            core = core[len(prefix):]
            break
    words = [word for word in re.findall(r"[a-z0-9]+", core) if word not in {"the", "a", "an", "and", "or", "to", "of", "for", "with", "when"}]
    if not words:
        words = [event.adapter, event.event_name, "learning"]
    return " ".join(words[:6])


def slugify(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "-".join(words[:8]) or "learning-candidate"


def processed_results_as_json(results: list[ProcessedEventResult]) -> str:
    return json.dumps([asdict(result) for result in results], ensure_ascii=False, indent=2)


def processed_results_as_text(results: list[ProcessedEventResult]) -> str:
    if not results:
        return "No new unprocessed events found."
    lines = []
    for result in results:
        line = f"- {result.status}: {result.event_path}"
        if result.candidate_path:
            line += f" -> {result.candidate_path}"
        elif result.reason:
            line += f" ({result.reason})"
        lines.append(line)
    return "\n".join(lines)
