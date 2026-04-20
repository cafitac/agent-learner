import json
from pathlib import Path

from agent_learner.core.context import detect_context, write_current_model


def test_detect_context_reads_project_language_framework_and_model(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        """
[project]
name = "sample"
dependencies = ["django", "pytest"]
""".strip(),
        encoding="utf-8",
    )
    write_current_model(tmp_path, "claude-sonnet-4-6")
    nested = tmp_path / "src" / "app"
    nested.mkdir(parents=True)

    context = detect_context(nested)
    assert context.project_name == tmp_path.name
    assert "python" in context.languages
    assert "django" in context.frameworks
    assert context.current_model == "claude-sonnet-4-6"
    assert json.loads(context.to_json())["project_name"] == tmp_path.name
