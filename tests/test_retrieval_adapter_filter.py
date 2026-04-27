"""Step 4 TDD — retrieval.py: adapter filter in retrieve_rules."""
from __future__ import annotations

from pathlib import Path

import pytest

from agent_learner.core.retrieval import RetrievalRequest, retrieve_rules
from agent_learner.core.lifecycle import LearningLifecycle
from agent_learner.core.models import LearningRule


def _promote_rule_with_harness(tmp_path, name, harness="universal"):
    """Promote a rule and rebuild index so retrieve_rules can find it."""
    root = Path(tmp_path) / ".agent-learner" / "learning"
    lc = LearningLifecycle(root)
    rule = LearningRule(
        name=name, rule="test rule", why="test why",
        scope="project", good_pattern="good", avoid_pattern="bad",
        harness=harness,
    )
    lc.promote(rule)
    return lc


class TestRetrievalRequestAdapter:
    def test_retrieval_request_has_adapter_field(self):
        req = RetrievalRequest(query="test")
        assert hasattr(req, "adapter")
        assert req.adapter is None

    def test_retrieval_request_adapter_set(self):
        req = RetrievalRequest(query="test", adapter="hermit")
        assert req.adapter == "hermit"


class TestAdapterFilter:
    def test_universal_rule_always_included(self, tmp_path):
        lc = _promote_rule_with_harness(tmp_path, "universal-rule", harness="universal")
        req = RetrievalRequest(query="test", adapter="claude")
        results = retrieve_rules(lc, req)
        names = [r.rule.name for r in results]
        assert "universal-rule" in names

    def test_matching_adapter_included(self, tmp_path):
        lc = _promote_rule_with_harness(tmp_path, "hermit-rule", harness="hermit")
        req = RetrievalRequest(query="test", adapter="hermit")
        results = retrieve_rules(lc, req)
        names = [r.rule.name for r in results]
        assert "hermit-rule" in names

    def test_non_matching_adapter_excluded(self, tmp_path):
        lc = _promote_rule_with_harness(tmp_path, "hermit-rule", harness="hermit")
        req = RetrievalRequest(query="test", adapter="claude")
        results = retrieve_rules(lc, req)
        names = [r.rule.name for r in results]
        assert "hermit-rule" not in names

    def test_no_adapter_request_includes_all(self, tmp_path):
        lc = _promote_rule_with_harness(tmp_path, "hermit-rule", harness="hermit")
        req = RetrievalRequest(query="test", adapter=None)
        results = retrieve_rules(lc, req)
        names = [r.rule.name for r in results]
        assert "hermit-rule" in names

    def test_empty_harness_treated_as_universal(self, tmp_path):
        lc = _promote_rule_with_harness(tmp_path, "empty-rule", harness="")
        req = RetrievalRequest(query="test", adapter="claude")
        results = retrieve_rules(lc, req)
        names = [r.rule.name for r in results]
        assert "empty-rule" in names
