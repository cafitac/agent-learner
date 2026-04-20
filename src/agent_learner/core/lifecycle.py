from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .models import LearningRule, RuleStatus, utc_now_iso, utc_today

SECTION_MAP = {
    "Rule": "rule",
    "Summary": "summary",
    "Why": "why",
    "Scope": "scope",
    "Good pattern": "good_pattern",
    "Avoid": "avoid_pattern",
    "Tags": "tags",
    "Triggers": "triggers",
    "Task types": "task_types",
    "File patterns": "file_patterns",
    "Projects": "projects",
    "Languages": "languages",
    "Frameworks": "frameworks",
    "Validated models": "validated_on_models",
    "Excluded models": "excluded_models",
    "Evidence": "evidence",
    "Source": "source",
}
LIST_SECTIONS = {
    "tags",
    "triggers",
    "task_types",
    "file_patterns",
    "projects",
    "languages",
    "frameworks",
    "validated_on_models",
    "excluded_models",
}
STATUS_DIRS: dict[RuleStatus, str] = {
    "draft": "drafts",
    "approved": "approved",
    "needs_review": "needs_review",
    "deprecated": "deprecated",
}


class LearningLifecycle:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.inbox = root / "inbox"
        self.drafts = root / "drafts"
        self.approved = root / "approved"
        self.needs_review = root / "needs_review"
        self.deprecated = root / "deprecated"
        for path in (self.inbox, self.drafts, self.approved, self.needs_review, self.deprecated):
            path.mkdir(parents=True, exist_ok=True)

    def save_draft(self, rule: LearningRule) -> Path:
        rule.status = "draft"
        return self.save_rule(rule)

    def promote(self, rule: LearningRule) -> Path:
        rule.status = "approved"
        rule.promote_count = max(rule.promote_count + 1, 1)
        rule.last_seen_at = utc_now_iso()
        return self.save_rule(rule)

    def mark_needs_review(self, rule: LearningRule) -> Path:
        rule.status = "needs_review"
        rule.last_seen_at = utc_now_iso()
        return self.save_rule(rule)

    def deprecate(self, rule: LearningRule) -> Path:
        rule.status = "deprecated"
        rule.last_seen_at = utc_now_iso()
        return self.save_rule(rule)

    def touch_rule(self, path_or_name: str | Path) -> Path:
        rule = self.load_rule(path_or_name)
        rule.use_count += 1
        rule.last_used = utc_today()
        return self.save_rule(rule)

    def validate_rule(self, path_or_name: str | Path, model: str) -> Path:
        rule = self.load_rule(path_or_name)
        if model not in rule.validated_on_models:
            rule.validated_on_models.append(model)
        rule.excluded_models = [entry for entry in rule.excluded_models if entry != model]
        if rule.status == "needs_review":
            rule.status = "approved"
        return self.save_rule(rule)

    def exclude_rule(self, path_or_name: str | Path, model: str) -> Path:
        rule = self.load_rule(path_or_name)
        if model not in rule.excluded_models:
            rule.excluded_models.append(model)
        rule.validated_on_models = [entry for entry in rule.validated_on_models if entry != model]
        if rule.status == "approved":
            rule.status = "needs_review"
        return self.save_rule(rule)

    def sweep_rules(
        self,
        *,
        current_model: str | None = None,
        unused_days: int = 30,
        needs_review_days: int = 30,
    ) -> list[dict[str, str]]:
        changes: list[dict[str, str]] = []
        now = datetime.now(timezone.utc)
        for rule in self.list_rules(statuses=["approved", "needs_review"]):
            previous_status = rule.status
            reason: str | None = None
            if rule.status == "approved":
                if rule.last_used:
                    try:
                        last_used = datetime.strptime(rule.last_used, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    except ValueError:
                        last_used = None
                    if last_used is not None and (now - last_used).days >= unused_days and rule.use_count > 0:
                        rule.status = "deprecated"
                        reason = f"unused {unused_days}d"
                if reason is None and self._model_change_requires_review(rule, current_model or ""):
                    rule.status = "needs_review"
                    reason = f"model change:{current_model}"
            elif rule.status == "needs_review":
                updated_at = self._parse_iso_datetime(rule.updated_at)
                if updated_at is not None and (now - updated_at).days >= needs_review_days:
                    rule.status = "deprecated"
                    reason = f"needs_review stale {needs_review_days}d"
            if reason is None or rule.status == previous_status:
                continue
            saved = self.save_rule(rule)
            changes.append(
                {
                    "name": rule.name,
                    "from": previous_status,
                    "to": rule.status,
                    "reason": reason,
                    "path": str(saved),
                }
            )
        return changes

    def save_rule(self, rule: LearningRule) -> Path:
        rule.ensure_defaults()
        rule.updated_at = utc_now_iso()
        if rule.token_estimate <= 0:
            rule.token_estimate = self.estimate_rule_tokens(rule)
        target = self.path_for_status(rule.status) / f"{rule.name}.md"
        self._remove_duplicates(rule.name, keep=target)
        target.write_text(self.render_rule(rule), encoding="utf-8")
        return target

    def load_rule(self, path_or_name: str | Path, statuses: list[RuleStatus] | None = None) -> LearningRule:
        path = self.resolve_rule_path(path_or_name, statuses=statuses)
        text = path.read_text(encoding="utf-8")
        metadata, sections = self.parse_rule_text(text)
        rule = LearningRule(
            name=str(metadata.get("name") or path.stem),
            rule=str(sections.get("rule") or metadata.get("description") or ""),
            why=str(sections.get("why") or ""),
            scope=str(sections.get("scope") or metadata.get("scope") or ""),
            good_pattern=str(sections.get("good_pattern") or ""),
            avoid_pattern=str(sections.get("avoid_pattern") or ""),
            summary=str(sections.get("summary") or metadata.get("description") or ""),
            tags=list(sections.get("tags") or metadata.get("tags") or []),
            triggers=list(sections.get("triggers") or metadata.get("triggers") or []),
            task_types=list(sections.get("task_types") or metadata.get("task_types") or []),
            file_patterns=list(sections.get("file_patterns") or metadata.get("file_patterns") or []),
            projects=list(sections.get("projects") or metadata.get("projects") or ["*"]),
            languages=list(sections.get("languages") or metadata.get("languages") or []),
            frameworks=list(sections.get("frameworks") or metadata.get("frameworks") or []),
            validated_on_models=list(sections.get("validated_on_models") or metadata.get("validated_on_models") or []),
            excluded_models=list(sections.get("excluded_models") or metadata.get("excluded_models") or []),
            model_dependency=str(metadata.get("model_dependency") or "low"),
            priority=str(metadata.get("priority") or "medium"),
            confidence=str(metadata.get("confidence") or "medium"),
            status=str(metadata.get("status") or self.status_for_path(path)),
            source=str(sections.get("source") or metadata.get("source") or "") or None,
            evidence=str(sections.get("evidence") or metadata.get("evidence") or "") or None,
            first_seen_at=str(metadata.get("first_seen_at") or "") or None,
            last_seen_at=str(metadata.get("last_seen_at") or "") or None,
            updated_at=str(metadata.get("updated_at") or "") or None,
            last_used=str(metadata.get("last_used") or "") or None,
            promote_count=int(metadata.get("promote_count") or 0),
            use_count=int(metadata.get("use_count") or 0),
            token_estimate=int(metadata.get("token_estimate") or 0),
        )
        rule.ensure_defaults()
        return rule

    def list_rule_paths(self, statuses: list[RuleStatus] | None = None) -> list[Path]:
        selected = statuses or list(STATUS_DIRS)
        paths: list[Path] = []
        for status in selected:
            paths.extend(sorted(self.path_for_status(status).glob("*.md")))
        return paths

    def list_rules(self, statuses: list[RuleStatus] | None = None) -> list[LearningRule]:
        return [self.load_rule(path) for path in self.list_rule_paths(statuses=statuses)]

    def resolve_rule_path(self, path_or_name: str | Path, statuses: list[RuleStatus] | None = None) -> Path:
        candidate = Path(path_or_name)
        if candidate.exists():
            return candidate
        selected = statuses or list(STATUS_DIRS)
        for status in selected:
            path = self.path_for_status(status) / f"{candidate.stem}.md"
            if path.exists():
                return path
        raise FileNotFoundError(f"rule not found: {path_or_name}")

    def path_for_status(self, status: str) -> Path:
        directory = STATUS_DIRS.get(status, "drafts")
        return self.root / directory

    def status_for_path(self, path: Path) -> RuleStatus:
        parent = path.parent.name
        for status, directory in STATUS_DIRS.items():
            if directory == parent:
                return status
        return "draft"

    def estimate_rule_tokens(self, rule: LearningRule) -> int:
        text = " ".join(
            filter(
                None,
                [
                    rule.name,
                    rule.summary or rule.rule,
                    rule.scope,
                    " ".join(rule.triggers),
                    " ".join(rule.task_types),
                    " ".join(rule.tags),
                    " ".join(rule.languages),
                    " ".join(rule.frameworks),
                ],
            )
        )
        return max(24, (len(text) // 4) + 1)

    def render_rule(self, rule: LearningRule) -> str:
        metadata = {
            "name": rule.name,
            "description": rule.summary or rule.rule,
            "type": "learned-feedback",
            "status": rule.status,
            "priority": rule.priority,
            "confidence": rule.confidence,
            "model_dependency": rule.model_dependency,
            "promote_count": rule.promote_count,
            "use_count": rule.use_count,
            "token_estimate": rule.token_estimate,
            "first_seen_at": rule.first_seen_at or "",
            "last_seen_at": rule.last_seen_at or "",
            "updated_at": rule.updated_at or "",
            "last_used": rule.last_used or "",
            "scope": rule.scope,
            "tags": rule.tags,
            "triggers": rule.triggers,
            "task_types": rule.task_types,
            "file_patterns": rule.file_patterns,
            "projects": rule.projects,
            "languages": rule.languages,
            "frameworks": rule.frameworks,
            "validated_on_models": rule.validated_on_models,
            "excluded_models": rule.excluded_models,
            "source": rule.source or "",
            "evidence": rule.evidence or "",
        }
        frontmatter = ["---"]
        for key, value in metadata.items():
            frontmatter.append(f"{key}: {self._encode_frontmatter_value(value)}")
        frontmatter.append("---")
        body = [
            "## Rule",
            rule.rule,
            "",
            "## Summary",
            rule.summary or rule.rule,
            "",
            "## Why",
            rule.why,
            "",
            "## Scope",
            rule.scope,
            "",
            "## Good pattern",
            rule.good_pattern,
            "",
            "## Avoid",
            rule.avoid_pattern,
        ]
        for section_name, values in (
            ("Tags", rule.tags),
            ("Triggers", rule.triggers),
            ("Task types", rule.task_types),
            ("File patterns", rule.file_patterns),
            ("Projects", rule.projects),
            ("Languages", rule.languages),
            ("Frameworks", rule.frameworks),
            ("Validated models", rule.validated_on_models),
            ("Excluded models", rule.excluded_models),
        ):
            if values:
                body.extend(["", f"## {section_name}", *[f"- {item}" for item in values]])
        if rule.evidence:
            body.extend(["", "## Evidence", rule.evidence])
        if rule.source:
            body.extend(["", "## Source", rule.source])
        return "\n".join(frontmatter + [""] + body).rstrip() + "\n"

    def parse_rule_text(self, text: str) -> tuple[dict[str, object], dict[str, object]]:
        metadata: dict[str, object] = {}
        sections: dict[str, object] = {}
        body = text
        if text.startswith("---\n"):
            end = text.find("\n---\n", 4)
            if end >= 0:
                frontmatter = text[4:end]
                body = text[end + 5 :]
                metadata = self._parse_frontmatter(frontmatter)
        current_section: str | None = None
        lines: list[str] = []
        for raw_line in body.splitlines():
            if raw_line.startswith("## "):
                self._flush_section(current_section, lines, sections)
                current_section = SECTION_MAP.get(raw_line[3:].strip())
                lines = []
            else:
                lines.append(raw_line)
        self._flush_section(current_section, lines, sections)
        return metadata, sections

    def _parse_frontmatter(self, text: str) -> dict[str, object]:
        metadata: dict[str, object] = {}
        for line in text.splitlines():
            if not line.strip() or ":" not in line:
                continue
            key, raw_value = line.split(":", 1)
            metadata[key.strip()] = self._decode_frontmatter_value(raw_value.strip())
        return metadata

    def _flush_section(self, section_name: str | None, lines: list[str], sections: dict[str, object]) -> None:
        if not section_name:
            return
        trimmed = [line.rstrip() for line in lines]
        while trimmed and not trimmed[0]:
            trimmed.pop(0)
        while trimmed and not trimmed[-1]:
            trimmed.pop()
        if not trimmed:
            sections[section_name] = [] if section_name in LIST_SECTIONS else ""
            return
        if section_name in LIST_SECTIONS:
            items = [line[2:].strip() if line.startswith("- ") else line.strip() for line in trimmed]
            sections[section_name] = [item for item in items if item]
            return
        sections[section_name] = "\n".join(trimmed).strip()

    def _remove_duplicates(self, name: str, keep: Path) -> None:
        for path in self.list_rule_paths():
            if path.name == keep.name and path != keep and path.exists():
                path.unlink()

    def _encode_frontmatter_value(self, value: object) -> str:
        if isinstance(value, list):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def _decode_frontmatter_value(self, value: str) -> object:
        if value == "":
            return ""
        if value.startswith("["):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return []
        if value.isdigit():
            return int(value)
        lowered = value.lower()
        if lowered in {"true", "false"}:
            return lowered == "true"
        return value

    def _parse_iso_datetime(self, value: str | None) -> datetime | None:
        if not value:
            return None
        normalized = value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized)
        except ValueError:
            return None

    def _model_change_requires_review(self, rule: LearningRule, current_model: str) -> bool:
        if not current_model:
            return False
        if current_model in rule.validated_on_models or current_model in rule.excluded_models:
            return False
        if rule.model_dependency == "none":
            return False
        has_same_line = any(self._is_upgrade(validated, current_model) for validated in rule.validated_on_models)
        if rule.model_dependency == "high":
            return True
        return not has_same_line

    def _is_upgrade(self, old: str, new: str) -> bool:
        return self._model_prefix(old) == self._model_prefix(new) and self._model_prefix(old) != ""

    def _model_prefix(self, model: str) -> str:
        base = (model or "").split(":", 1)[0]
        parts = [part for part in base.split("-") if part and not part[0].isdigit()]
        return "-".join(parts)
