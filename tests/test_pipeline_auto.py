"""Step 3 TDD — pipeline_auto.py: AutoLearningPipeline."""
from __future__ import annotations

from pathlib import Path

import pytest

from agent_learner.core.llm import LearnerLLM
from agent_learner.core.models import LearningRule, ModelPerf
from agent_learner.core.pipeline_auto import AutoLearningPipeline, ProcessedSessionResult


class MockLLM:
    """Test double for LearnerLLM."""
    def __init__(self, result=None, *, should_hang=False):
        self._result = result
        self._should_hang = should_hang
        self.called = False
        self.call_count = 0

    def extract(self, prompt, system=None, timeout=30.0):
        self.called = True
        self.call_count += 1
        if self._should_hang:
            import time
            time.sleep(timeout + 5)
        return self._result


class TimeoutLLM:
    """LLM that always times out."""
    def extract(self, prompt, system=None, timeout=30.0):
        import time
        time.sleep(timeout + 10)
        return {"rule": "never"}


def _make_pipeline(tmp_path, llm, **kwargs):
    return AutoLearningPipeline(tmp_path, llm, **kwargs)


class TestProcessSession:
    def test_skips_low_tool_count(self, tmp_path):
        llm = MockLLM(result={"rule": "test"})
        pipeline = _make_pipeline(tmp_path, llm)
        result = pipeline.process_session(
            session_id="s1", adapter="hermit", outcome="success",
            tool_call_count=3, cwd=str(tmp_path), model_id="glm-4",
        )
        assert result.rules_extracted == 0
        assert llm.called is False

    def test_skips_cancelled(self, tmp_path):
        llm = MockLLM(result={"rule": "test"})
        pipeline = _make_pipeline(tmp_path, llm)
        result = pipeline.process_session(
            session_id="s1", adapter="hermit", outcome="cancelled",
            tool_call_count=20, cwd=str(tmp_path), model_id="glm-4",
        )
        assert result.rules_extracted == 0
        assert llm.called is False

    def test_extracts_and_promotes(self, tmp_path):
        llm = MockLLM(result={
            "name": "always-test", "rule": "test", "why": "w",
            "scope": "s", "good_pattern": "g", "avoid_pattern": "a",
        })
        pipeline = _make_pipeline(tmp_path, llm)
        result = pipeline.process_session(
            session_id="s1", adapter="hermit", outcome="success",
            tool_call_count=10, cwd=str(tmp_path), model_id="glm-4",
        )
        assert result.rules_extracted == 1
        assert result.rules_promoted == 1
        assert result.error is None

    def test_llm_returns_none_skips(self, tmp_path):
        llm = MockLLM(result=None)
        pipeline = _make_pipeline(tmp_path, llm)
        result = pipeline.process_session(
            session_id="s1", adapter="hermit", outcome="success",
            tool_call_count=10, cwd=str(tmp_path), model_id="glm-4",
        )
        assert result.rules_extracted == 0

    def test_llm_timeout_returns_skip(self, tmp_path):
        llm = TimeoutLLM()
        pipeline = _make_pipeline(tmp_path, llm, verify_timeout=1)
        result = pipeline.process_session(
            session_id="s1", adapter="hermit", outcome="success",
            tool_call_count=10, cwd=str(tmp_path), model_id="glm-4",
        )
        assert result.rules_extracted == 0
        assert result.error is None

    def test_refreshes_existing_rule(self, tmp_path):
        """When a rule with the same name already exists, refresh it."""
        pipeline = _make_pipeline(tmp_path, MockLLM())
        # Pre-create a rule
        from agent_learner.core.lifecycle import LearningLifecycle
        root = Path(tmp_path) / ".agent-learner" / "learning"
        lc = LearningLifecycle(root)
        existing = LearningRule(
            name="always-test", rule="old rule", why="w", scope="s",
            good_pattern="g", avoid_pattern="a", status="approved",
        )
        lc.promote(existing)

        llm = MockLLM(result={
            "name": "always-test", "rule": "new rule", "why": "w",
            "scope": "s", "good_pattern": "g", "avoid_pattern": "a",
        })
        pipeline2 = _make_pipeline(tmp_path, llm)
        result = pipeline2.process_session(
            session_id="s1", adapter="hermit", outcome="success",
            tool_call_count=10, cwd=str(tmp_path), model_id="glm-4",
        )
        assert result.rules_refreshed == 1
        assert result.rules_promoted == 0

    def test_result_has_session_id_and_adapter(self, tmp_path):
        llm = MockLLM(result=None)
        pipeline = _make_pipeline(tmp_path, llm)
        result = pipeline.process_session(
            session_id="s42", adapter="claude", outcome="success",
            tool_call_count=3, cwd=str(tmp_path), model_id="glm-4",
        )
        assert result.session_id == "s42"
        assert result.adapter == "claude"


class TestRecordRuleUsed:
    def test_updates_model_perf(self, tmp_path):
        """record_rule_used increments model performance counters."""
        llm = MockLLM(result={
            "name": "perf-rule", "rule": "test", "why": "w",
            "scope": "s", "good_pattern": "g", "avoid_pattern": "a",
        })
        p = _make_pipeline(tmp_path, llm)
        p.process_session(
            session_id="s1", adapter="hermit", outcome="success",
            tool_call_count=10, cwd=str(tmp_path), model_id="glm-4",
        )
        p.record_rule_used("perf-rule", outcome=True, model_id="glm-4")
        p.record_rule_used("perf-rule", outcome=True, model_id="glm-4")
        p.record_rule_used("perf-rule", outcome=False, model_id="glm-4")

        rule = p.get_rule("perf-rule")
        assert rule is not None
        assert rule.model_performance["glm-4"].use_count == 3
        assert rule.model_performance["glm-4"].success_count == 2
        assert rule.model_performance["glm-4"].fail_count == 1

    def test_updates_global_counts(self, tmp_path):
        """record_rule_used updates global success/fail counts."""
        llm = MockLLM(result={
            "name": "cnt-rule", "rule": "test", "why": "w",
            "scope": "s", "good_pattern": "g", "avoid_pattern": "a",
        })
        p = _make_pipeline(tmp_path, llm)
        p.process_session(
            session_id="s1", adapter="hermit", outcome="success",
            tool_call_count=10, cwd=str(tmp_path), model_id="glm-4",
        )
        p.record_rule_used("cnt-rule", outcome=True, model_id="glm-4")
        p.record_rule_used("cnt-rule", outcome=False, model_id="glm-4")

        rule = p.get_rule("cnt-rule")
        assert rule is not None
        assert rule.success_count == 1
        assert rule.fail_count == 1


class TestModelClassification:
    def test_validated_after_high_success(self, tmp_path):
        """Model with success_rate >= 0.7 after 5 uses -> validated_on_models."""
        llm = MockLLM(result={
            "name": "val-rule", "rule": "test", "why": "w",
            "scope": "s", "good_pattern": "g", "avoid_pattern": "a",
        })
        p = _make_pipeline(tmp_path, llm, min_uses_before_classify=5)
        p.process_session(
            session_id="s1", adapter="hermit", outcome="success",
            tool_call_count=10, cwd=str(tmp_path), model_id="glm-4",
        )
        for _ in range(5):
            p.record_rule_used("val-rule", outcome=True, model_id="glm-4")

        rule = p.get_rule("val-rule")
        assert rule is not None
        assert "glm-4" in rule.validated_on_models

    def test_excluded_after_low_success(self, tmp_path):
        """Model with success_rate < 0.4 after 5 uses -> excluded_models."""
        llm = MockLLM(result={
            "name": "exc-rule", "rule": "test", "why": "w",
            "scope": "s", "good_pattern": "g", "avoid_pattern": "a",
        })
        p = _make_pipeline(tmp_path, llm, min_uses_before_classify=5, excluded_threshold=0.4)
        p.process_session(
            session_id="s1", adapter="hermit", outcome="success",
            tool_call_count=10, cwd=str(tmp_path), model_id="bad-model",
        )
        # 1 success, 4 failures -> rate = 0.2
        p.record_rule_used("exc-rule", outcome=True, model_id="bad-model")
        for _ in range(4):
            p.record_rule_used("exc-rule", outcome=False, model_id="bad-model")

        rule = p.get_rule("exc-rule")
        assert rule is not None
        assert "bad-model" in rule.excluded_models


class TestAutoDeprecate:
    def test_needs_review_after_low_success(self, tmp_path):
        """Rule with success_rate < 0.4 after 5+ uses -> needs_review=True."""
        llm = MockLLM(result={
            "name": "dep-rule", "rule": "test", "why": "w",
            "scope": "s", "good_pattern": "g", "avoid_pattern": "a",
        })
        p = _make_pipeline(
            tmp_path, llm,
            min_uses_before_eval=5,
            success_rate_threshold=0.4,
        )
        p.process_session(
            session_id="s1", adapter="hermit", outcome="success",
            tool_call_count=10, cwd=str(tmp_path), model_id="glm-4",
        )
        # 2 successes, 4 failures -> rate = 0.333
        for _ in range(2):
            p.record_rule_used("dep-rule", outcome=True, model_id="glm-4")
        for _ in range(4):
            p.record_rule_used("dep-rule", outcome=False, model_id="glm-4")

        rule = p.get_rule("dep-rule")
        assert rule is not None
        assert rule.needs_review is True
