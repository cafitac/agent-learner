"""Step 1 TDD — models.py v2: ModelPerf + performance tracking fields."""
from __future__ import annotations

import pytest

from agent_learner.core.models import LearningRule, ModelPerf


class TestModelPerf:
    def test_model_perf_success_rate(self):
        p = ModelPerf(use_count=10, success_count=8, fail_count=2)
        assert p.success_rate == pytest.approx(0.8)

    def test_model_perf_success_rate_zero_division(self):
        p = ModelPerf()
        assert p.success_rate == 0.0

    def test_model_perf_defaults(self):
        p = ModelPerf()
        assert p.use_count == 0
        assert p.success_count == 0
        assert p.fail_count == 0


class TestLearningRuleV2Fields:
    def test_learning_rule_has_model_perf_field(self):
        rule = LearningRule(name="r", rule="r", why="w", scope="s",
                            good_pattern="g", avoid_pattern="a")
        assert hasattr(rule, "model_performance")
        assert isinstance(rule.model_performance, dict)

    def test_learning_rule_has_verify_cmd(self):
        rule = LearningRule(name="r", rule="r", why="w", scope="s",
                            good_pattern="g", avoid_pattern="a")
        assert rule.verify_cmd == ""

    def test_learning_rule_has_needs_review(self):
        rule = LearningRule(name="r", rule="r", why="w", scope="s",
                            good_pattern="g", avoid_pattern="a")
        assert rule.needs_review is False

    def test_learning_rule_has_success_fail_counts(self):
        rule = LearningRule(name="r", rule="r", why="w", scope="s",
                            good_pattern="g", avoid_pattern="a")
        assert rule.success_count == 0
        assert rule.fail_count == 0

    def test_learning_rule_has_harness(self):
        rule = LearningRule(name="r", rule="r", why="w", scope="s",
                            good_pattern="g", avoid_pattern="a")
        assert rule.harness == "universal"

    def test_learning_rule_model_performance_populated(self):
        perf = ModelPerf(use_count=5, success_count=4, fail_count=1)
        rule = LearningRule(
            name="r", rule="r", why="w", scope="s",
            good_pattern="g", avoid_pattern="a",
            model_performance={"glm-4": perf},
        )
        assert "glm-4" in rule.model_performance
        assert rule.model_performance["glm-4"].success_rate == pytest.approx(0.8)
