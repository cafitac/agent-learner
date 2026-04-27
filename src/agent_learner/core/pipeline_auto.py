"""Auto-learning pipeline for processing sessions and managing rule lifecycle."""
from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from .lifecycle import LearningLifecycle
from .models import LearningRule, ModelPerf
from .storage import canonical_learning_root

if TYPE_CHECKING:
    from .llm import LearnerLLM


@dataclass(slots=True)
class ProcessedSessionResult:
    """Result of processing a single session through the auto-learning pipeline."""
    session_id: str
    adapter: str
    rules_extracted: int = 0
    rules_promoted: int = 0
    rules_refreshed: int = 0
    rules_skipped: int = 0
    error: str | None = None


class AutoLearningPipeline:
    """Automated pipeline that extracts, promotes, and manages learning rules."""

    def __init__(
        self,
        project_root: Path,
        llm: "LearnerLLM",
        *,
        auto_promote: bool = True,
        verify_timeout: int = 30,
        min_uses_before_eval: int = 5,
        success_rate_threshold: float = 0.4,
        validated_threshold: float = 0.7,
        excluded_threshold: float = 0.4,
        min_uses_before_classify: int = 5,
    ) -> None:
        self.project_root = Path(project_root)
        self.llm = llm
        self.auto_promote = auto_promote
        self.verify_timeout = verify_timeout
        self.min_uses_before_eval = min_uses_before_eval
        self.success_rate_threshold = success_rate_threshold
        self.validated_threshold = validated_threshold
        self.excluded_threshold = excluded_threshold
        self.min_uses_before_classify = min_uses_before_classify
        self._root = canonical_learning_root(self.project_root)
        self._lifecycle = LearningLifecycle(self._root)

    def _get_lifecycle(self) -> LearningLifecycle:
        """Get a fresh lifecycle (dirs may have been created since init)."""
        return LearningLifecycle(self._root)

    # -- sidecar v2 persistence -----------------------------------------------

    def _sidecar_path(self, rule_path: Path) -> Path:
        """Return the .v2.json sidecar path for a rule .md file."""
        return rule_path.with_suffix(".md.v2.json")

    def _save_v2_sidecar(self, rule: LearningRule) -> None:
        """Persist v2 fields the frozen lifecycle doesn't know about."""
        lc = self._get_lifecycle()
        rule_path = lc.resolve_rule_path(rule.name)
        sidecar = self._sidecar_path(rule_path)
        data = {
            "success_count": rule.success_count,
            "fail_count": rule.fail_count,
            "needs_review": rule.needs_review,
            "verify_cmd": rule.verify_cmd,
            "harness": rule.harness,
            "model_performance": {
                k: {"use_count": v.use_count, "success_count": v.success_count, "fail_count": v.fail_count}
                for k, v in rule.model_performance.items()
            },
            "validated_on_models": rule.validated_on_models,
            "excluded_models": rule.excluded_models,
        }
        sidecar.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _load_v2_sidecar(self, rule: LearningRule) -> None:
        """Overlay v2 fields from sidecar onto a rule loaded by frozen lifecycle."""
        lc = self._get_lifecycle()
        try:
            rule_path = lc.resolve_rule_path(rule.name)
        except FileNotFoundError:
            return
        sidecar = self._sidecar_path(rule_path)
        if not sidecar.exists():
            return
        try:
            data = json.loads(sidecar.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return
        rule.success_count = data.get("success_count", 0)
        rule.fail_count = data.get("fail_count", 0)
        rule.needs_review = data.get("needs_review", False)
        rule.verify_cmd = data.get("verify_cmd", "")
        rule.harness = data.get("harness", "universal")
        rule.validated_on_models = data.get("validated_on_models", [])
        rule.excluded_models = data.get("excluded_models", [])
        raw_mp = data.get("model_performance", {})
        rule.model_performance = {
            k: ModelPerf(**v) for k, v in raw_mp.items()
        }

    def _load_rule_with_v2(self, rule_name: str) -> LearningRule | None:
        """Load a rule through frozen lifecycle, then overlay v2 sidecar fields."""
        lc = self._get_lifecycle()
        try:
            rule = lc.load_rule(
                rule_name,
                statuses=["approved", "needs_review", "deprecated", "draft"],
            )
        except FileNotFoundError:
            return None
        self._load_v2_sidecar(rule)
        return rule

    # -- public API -----------------------------------------------------------

    def process_session(
        self,
        *,
        session_id: str,
        adapter: str,
        outcome: Literal["success", "failure", "cancelled"],
        tool_call_count: int,
        cwd: str,
        model_id: str,
        pytest_output: str | None = None,
        transcript_path: str | None = None,
    ) -> ProcessedSessionResult:
        result = ProcessedSessionResult(session_id=session_id, adapter=adapter)

        # 1. Skip low tool count
        if tool_call_count < 5:
            result.rules_skipped = 1
            return result

        # 2. Skip cancelled
        if outcome == "cancelled":
            result.rules_skipped = 1
            return result

        # 3. LLM extract with timeout enforcement
        prompt = self._build_prompt(outcome, tool_call_count, pytest_output)
        extracted = self._extract_with_timeout(prompt)

        # 4. Extract returned None -> skip
        if extracted is None:
            result.rules_skipped = 1
            return result

        result.rules_extracted = 1
        name = extracted.get("name", "unnamed-rule")

        # 5. Check for existing rule
        lc = self._get_lifecycle()
        existing = self._find_existing_rule(lc, name)

        if existing is not None:
            # Refresh existing
            lc.refresh(
                existing,
                source_adapter=adapter,
                evidence_excerpt=str(outcome),
            )
            result.rules_refreshed = 1
        elif self.auto_promote:
            # Promote new rule
            rule = LearningRule(
                name=name,
                rule=extracted.get("rule", ""),
                why=extracted.get("why", ""),
                scope=extracted.get("scope", ""),
                good_pattern=extracted.get("good_pattern", ""),
                avoid_pattern=extracted.get("avoid_pattern", ""),
                tags=extracted.get("tags", []),
                verify_cmd=extracted.get("verify_cmd", ""),
                harness=adapter,
                source_adapter=adapter,
            )
            lc.promote(rule)
            # Save initial v2 sidecar
            self._save_v2_sidecar(rule)
            result.rules_promoted = 1

        return result

    def record_rule_used(
        self,
        rule_name: str,
        *,
        outcome: bool | None,
        model_id: str,
    ) -> None:
        rule = self._load_rule_with_v2(rule_name)
        if rule is None:
            return

        # Update model performance
        if model_id not in rule.model_performance:
            rule.model_performance[model_id] = ModelPerf()

        perf = rule.model_performance[model_id]
        perf.use_count += 1
        if outcome is True:
            perf.success_count += 1
            rule.success_count += 1
        elif outcome is False:
            perf.fail_count += 1
            rule.fail_count += 1

        # Increment use count
        rule.use_count += 1

        # Model classification
        self._maybe_update_model_classification(rule, model_id)

        # Auto-deprecate check
        self._maybe_auto_deprecate(rule)

        # Save via frozen lifecycle (handles .md), then save v2 sidecar
        lc = self._get_lifecycle()
        lc.save_rule(rule)
        self._save_v2_sidecar(rule)

    def get_rule(self, rule_name: str) -> LearningRule | None:
        """Public helper to load a rule with v2 fields overlaid."""
        return self._load_rule_with_v2(rule_name)

    # -- internal helpers -----------------------------------------------------

    def _extract_with_timeout(self, prompt: str) -> dict | None:
        """Call LLM.extract with enforced timeout regardless of LLM implementation."""
        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.llm.extract, prompt, None, self.verify_timeout)
                return future.result(timeout=self.verify_timeout + 2)
        except FuturesTimeoutError:
            return None
        except Exception:
            return None

    def _maybe_update_model_classification(self, rule: LearningRule, model_id: str) -> None:
        perf = rule.model_performance.get(model_id)
        if perf is None:
            return
        if perf.use_count < self.min_uses_before_classify:
            return

        if perf.success_rate >= self.validated_threshold:
            if model_id not in rule.validated_on_models:
                rule.validated_on_models.append(model_id)
            rule.excluded_models = [m for m in rule.excluded_models if m != model_id]
        elif perf.success_rate < self.excluded_threshold:
            if model_id not in rule.excluded_models:
                rule.excluded_models.append(model_id)
            rule.validated_on_models = [m for m in rule.validated_on_models if m != model_id]

    def _maybe_auto_deprecate(self, rule: LearningRule) -> None:
        total = rule.success_count + rule.fail_count
        if total < self.min_uses_before_eval:
            return
        rate = rule.success_count / total if total > 0 else 0.0

        if rate < self.success_rate_threshold:
            if not rule.needs_review:
                rule.needs_review = True
            else:
                # Already flagged, escalate to deprecated
                rule.status = "deprecated"

    def _find_existing_rule(self, lc: LearningLifecycle, name: str) -> str | None:
        """Return rule name if it already exists in any status bucket, else None."""
        try:
            lc.resolve_rule_path(name, statuses=["approved", "needs_review", "deprecated", "draft"])
            return name
        except FileNotFoundError:
            return None

    def _build_prompt(
        self,
        outcome: str,
        tool_call_count: int,
        pytest_output: str | None,
    ) -> str:
        if outcome == "success":
            return (
                f"Analyze this successful coding session ({tool_call_count} tool calls). "
                "Extract a reusable learning rule as JSON with keys: "
                "name, rule, why, scope, good_pattern, avoid_pattern, tags, verify_cmd"
            )
        prompt = (
            f"Analyze this failed coding session ({tool_call_count} tool calls). "
            "Extract a reusable learning rule that would prevent this failure as JSON with keys: "
            "name, rule, why, scope, good_pattern, avoid_pattern, tags, verify_cmd"
        )
        if pytest_output:
            prompt += f"\nPytest output:\n{pytest_output[:2000]}"
        return prompt
