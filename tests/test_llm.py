"""Step 2 TDD — llm.py: LearnerLLM protocol + ConfiguredLearnerLLM."""
from __future__ import annotations

import time
from pathlib import Path

import pytest

from agent_learner.core.llm import ConfiguredLearnerLLM, LearnerLLM


class TestLearnerLLMProtocol:
    def test_learner_llm_protocol_satisfied_by_mock(self):
        class MockLLM:
            def extract(self, prompt, system=None, timeout=30.0):
                return {"rule": "test rule", "why": "test why"}
        llm = MockLLM()
        assert isinstance(llm, LearnerLLM)

    def test_learner_llm_protocol_not_satisfied_without_extract(self):
        class NotLLM:
            pass
        assert not isinstance(NotLLM(), LearnerLLM)


class TestConfiguredLearnerLLM:
    def test_loads_project_config(self, tmp_path):
        config = tmp_path / ".agent-learner" / "config.json"
        config.parent.mkdir(parents=True)
        config.write_text('{"llm": {"provider": "anthropic", "model": "claude-haiku-4-5"}}')
        llm = ConfiguredLearnerLLM(project_root=tmp_path)
        assert llm.model == "claude-haiku-4-5"
        assert llm.provider == "anthropic"

    def test_loads_global_config_fallback(self, tmp_path, monkeypatch):
        global_home = tmp_path / "global_home"
        global_home.mkdir()
        config = global_home / "config.json"
        config.write_text('{"llm": {"provider": "openai", "model": "gpt-4o"}}')
        monkeypatch.setenv("AGENT_LEARNER_HOME", str(global_home))
        # no project config
        llm = ConfiguredLearnerLLM(project_root=tmp_path / "nonexistent")
        assert llm.model == "gpt-4o"

    def test_defaults_when_no_config(self, tmp_path, monkeypatch):
        monkeypatch.setenv("AGENT_LEARNER_HOME", str(tmp_path / "nohome"))
        llm = ConfiguredLearnerLLM(project_root=tmp_path / "noproj")
        assert llm.model is not None  # has some default
        assert llm.provider is not None

    def test_extract_returns_none_on_timeout(self, tmp_path):
        class SlowConfiguredLLM(ConfiguredLearnerLLM):
            def _call_api(self, prompt, system=None):
                time.sleep(60)
                return {"rule": "never reached"}

        llm = SlowConfiguredLLM(project_root=tmp_path)
        result = llm.extract("test prompt", timeout=0.1)
        assert result is None

    def test_extract_returns_none_on_exception(self, tmp_path):
        class FailLLM(ConfiguredLearnerLLM):
            def _call_api(self, prompt, system=None):
                raise RuntimeError("API error")

        llm = FailLLM(project_root=tmp_path)
        result = llm.extract("test prompt")
        assert result is None

    def test_extract_returns_dict_on_success(self, tmp_path):
        class SuccessLLM(ConfiguredLearnerLLM):
            def _call_api(self, prompt, system=None):
                return {"name": "test-rule", "rule": "always test", "why": "because"}

        llm = SuccessLLM(project_root=tmp_path)
        result = llm.extract("test prompt")
        assert result is not None
        assert result["name"] == "test-rule"
