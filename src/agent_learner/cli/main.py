from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import sys
from pathlib import Path

from agent_learner.adapters import install_claude_adapter, install_codex_adapter
from agent_learner.adapters.codex_context import (
    build_codex_user_prompt_hook_output,
    format_retrieval_results_as_json,
    format_retrieval_results_as_text,
    render_codex_learning_context,
)
from agent_learner.core.context import detect_context, write_current_model
from agent_learner.core.events import build_learning_event, write_learning_event
from agent_learner.core.pipeline import process_unprocessed_events, processed_results_as_json, processed_results_as_text
from agent_learner.core.lifecycle import LearningLifecycle
from agent_learner.core.models import LearningRule


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-learner")
    sub = parser.add_subparsers(dest="command")

    init_cmd = sub.add_parser("init")
    init_cmd.add_argument("--root", default=".agent-learner")

    codex_cmd = sub.add_parser("install-codex")
    codex_cmd.add_argument("--target", default=".")

    claude_cmd = sub.add_parser("install-claude")
    claude_cmd.add_argument("--target", default=".")

    bootstrap_cmd = sub.add_parser("bootstrap")
    bootstrap_cmd.add_argument("--target", default=".")
    bootstrap_cmd.add_argument(
        "--adapters",
        default="codex,claude",
        help="Comma-separated adapter list: codex, claude",
    )

    promote_cmd = sub.add_parser("promote-demo")
    promote_cmd.add_argument("--root", default=".agent-learner")

    context_detect_cmd = sub.add_parser("detect-context")
    context_detect_cmd.add_argument("--project-root", default=".")

    set_model_cmd = sub.add_parser("set-model")
    set_model_cmd.add_argument("--project-root", default=".")
    set_model_cmd.add_argument("--model", required=True)

    validate_cmd = sub.add_parser("validate-rule")
    validate_cmd.add_argument("--project-root", default=".")
    validate_cmd.add_argument("--name", required=True)
    validate_cmd.add_argument("--model", required=True)

    exclude_cmd = sub.add_parser("exclude-rule")
    exclude_cmd.add_argument("--project-root", default=".")
    exclude_cmd.add_argument("--name", required=True)
    exclude_cmd.add_argument("--model", required=True)

    sweep_cmd = sub.add_parser("sweep")
    sweep_cmd.add_argument("--project-root", default=".")
    sweep_cmd.add_argument("--unused-days", type=int, default=30)
    sweep_cmd.add_argument("--needs-review-days", type=int, default=30)
    sweep_cmd.add_argument("--format", choices=["text", "json"], default="text")

    retrieve_cmd = sub.add_parser("retrieve")
    retrieve_cmd.add_argument("--project-root", default=".")
    retrieve_cmd.add_argument("--prompt", required=True)
    retrieve_cmd.add_argument("--scope")
    retrieve_cmd.add_argument("--task-type")
    retrieve_cmd.add_argument("--file", action="append", dest="files", default=[])
    retrieve_cmd.add_argument("--limit", type=int, default=3)
    retrieve_cmd.add_argument("--token-budget", type=int)
    retrieve_cmd.add_argument("--include-needs-review", action="store_true")
    retrieve_cmd.add_argument("--format", choices=["text", "json"], default="text")

    smoke_cmd = sub.add_parser("qa-codex-smoke")
    smoke_cmd.add_argument("--project-root", default=".")
    smoke_cmd.add_argument("--prompt", default="fix the codex prompt hook and keep tests green")

    claude_smoke_cmd = sub.add_parser("qa-claude-smoke")
    claude_smoke_cmd.add_argument("--project-root", default=".")

    capture_cmd = sub.add_parser("capture-event")
    capture_cmd.add_argument("--project-root", default=".")
    capture_cmd.add_argument("--adapter", required=True, choices=["codex", "claude"])
    capture_cmd.add_argument("--event-name", required=True)
    capture_cmd.add_argument("--session-id")
    capture_cmd.add_argument("--transcript-path")

    process_cmd = sub.add_parser("process-events")
    process_cmd.add_argument("--project-root", default=".")
    process_cmd.add_argument("--adapter", choices=["codex", "claude"])
    process_cmd.add_argument("--limit", type=int)
    process_cmd.add_argument("--format", choices=["text", "json"], default="text")

    context_cmd = sub.add_parser("render-codex-context")
    context_cmd.add_argument("--project-root", default=".")
    context_cmd.add_argument("--prompt", required=True)
    context_cmd.add_argument("--scope")
    context_cmd.add_argument("--task-type")
    context_cmd.add_argument("--file", action="append", dest="files", default=[])
    context_cmd.add_argument("--limit", type=int, default=3)
    context_cmd.add_argument("--token-budget", type=int, default=240)
    context_cmd.add_argument("--format", choices=["text", "json", "hook-json"], default="text")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "init":
        lifecycle = LearningLifecycle(Path(args.root))
        print(f"initialized:{lifecycle.root}")
        return 0
    if args.command == "install-codex":
        written = install_codex_adapter(Path(args.target).resolve())
        for path in written:
            print(path)
        return 0
    if args.command == "install-claude":
        written = install_claude_adapter(Path(args.target).resolve())
        for path in written:
            print(path)
        return 0
    if args.command == "bootstrap":
        target = Path(args.target).resolve()
        adapters = [item.strip() for item in args.adapters.split(",") if item.strip()]
        written: list[Path] = []
        if "codex" in adapters:
            written.extend(install_codex_adapter(target))
        if "claude" in adapters:
            written.extend(install_claude_adapter(target))
        for path in dict.fromkeys(written):
            print(path)
        return 0
    if args.command == "promote-demo":
        lifecycle = LearningLifecycle(Path(args.root))
        rule = LearningRule(
            name="demo-rule",
            rule="Always keep the lifecycle deterministic.",
            why="Predictable state transitions make review and automation easier.",
            scope="learning lifecycle",
            good_pattern="promote draft -> approved with explicit state",
            avoid_pattern="implicit or silent rule transitions",
            summary="Keep rule transitions explicit and deterministic.",
            task_types=["refactor", "cli"],
            triggers=["lifecycle", "state transition"],
            priority="high",
            confidence="high",
        )
        path = lifecycle.promote(rule)
        print(path)
        return 0
    if args.command == "detect-context":
        print(detect_context(Path(args.project_root).resolve()).to_json())
        return 0
    if args.command == "set-model":
        path = write_current_model(Path(args.project_root).resolve(), args.model)
        print(path)
        return 0
    if args.command == "validate-rule":
        project_root = Path(args.project_root).resolve()
        lifecycle = LearningLifecycle(project_root / ".codex" / "references" / "learning")
        path = lifecycle.validate_rule(args.name, args.model)
        print(path)
        return 0
    if args.command == "exclude-rule":
        project_root = Path(args.project_root).resolve()
        lifecycle = LearningLifecycle(project_root / ".codex" / "references" / "learning")
        path = lifecycle.exclude_rule(args.name, args.model)
        print(path)
        return 0
    if args.command == "sweep":
        project_root = Path(args.project_root).resolve()
        lifecycle = LearningLifecycle(project_root / ".codex" / "references" / "learning")
        context = detect_context(project_root)
        changes = lifecycle.sweep_rules(
            current_model=context.current_model,
            unused_days=args.unused_days,
            needs_review_days=args.needs_review_days,
        )
        if args.format == "json":
            print(json.dumps(changes, ensure_ascii=False, indent=2))
        else:
            if not changes:
                print("nothing swept.")
            else:
                for change in changes:
                    print(f"- {change['name']}: {change['from']} -> {change['to']} ({change['reason']})")
        return 0
    if args.command == "retrieve":
        project_root = Path(args.project_root).resolve()
        if args.format == "json":
            print(
                format_retrieval_results_as_json(
                    project_root,
                    args.prompt,
                    scope=args.scope,
                    task_type=args.task_type,
                    file_paths=args.files,
                    limit=args.limit,
                    token_budget=args.token_budget,
                    include_needs_review=args.include_needs_review,
                )
            )
        else:
            print(
                format_retrieval_results_as_text(
                    project_root,
                    args.prompt,
                    scope=args.scope,
                    task_type=args.task_type,
                    file_paths=args.files,
                    limit=args.limit,
                    token_budget=args.token_budget,
                    include_needs_review=args.include_needs_review,
                )
            )
        return 0
    if args.command == "capture-event":
        try:
            payload = json.load(sys.stdin)
        except json.JSONDecodeError:
            payload = {}
        except Exception:
            payload = {}
        target = write_learning_event(
            Path(args.project_root).resolve(),
            build_learning_event(
                adapter=args.adapter,
                event_name=args.event_name,
                cwd=str(Path(args.project_root).resolve()),
                session_id=args.session_id,
                transcript_path=args.transcript_path,
                payload=payload,
            ),
        )
        print(target)
        return 0

    if args.command == "process-events":
        project_root = Path(args.project_root).resolve()
        results = process_unprocessed_events(project_root, adapter=args.adapter, limit=args.limit)
        if args.format == "json":
            print(processed_results_as_json(results))
        else:
            print(processed_results_as_text(results))
        return 0

    if args.command == "qa-claude-smoke":
        target = Path(args.project_root).resolve()
        cleanup_dir: tempfile.TemporaryDirectory[str] | None = None
        if str(target) == str(Path('.').resolve()):
            cleanup_dir = tempfile.TemporaryDirectory(prefix="agent-learner-claude-smoke-")
            target = Path(cleanup_dir.name).resolve()
        install_claude_adapter(target)
        transcript_path = target / "transcript.jsonl"
        transcript_path.write_text(json.dumps({"message": "Always keep durable workflow rules short and reusable."}) + "\n", encoding="utf-8")
        script_path = target / ".claude" / "hooks" / "auto_session_learning.py"
        env = dict(os.environ)
        env["PATH"] = f"{Path(sys.executable).parent}:{env.get('PATH', '')}"
        src_path = str(Path(__file__).resolve().parents[2])
        env["PYTHONPATH"] = f"{src_path}:{env.get('PYTHONPATH', '')}" if env.get("PYTHONPATH") else src_path
        result = subprocess.run(
            [sys.executable, str(script_path)],
            input=json.dumps(
                {
                    "cwd": str(target),
                    "session_id": "claude-smoke-session",
                    "transcript_path": str(transcript_path),
                    "message": "Always keep durable workflow rules short and reusable.",
                }
            ),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        event_files = sorted((target / ".agent-learner" / "events" / "claude").glob("*.json"))
        candidate_files = sorted((target / ".agent-learner" / "candidates" / "claude").glob("*.md"))
        print(
            json.dumps(
                {
                    "project_root": str(target),
                    "hook_script": str(script_path),
                    "returncode": result.returncode,
                    "event_files": [str(path) for path in event_files],
                    "candidate_files": [str(path) for path in candidate_files],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if cleanup_dir is not None:
            cleanup_dir.cleanup()
        return 0 if result.returncode == 0 else result.returncode

    if args.command == "qa-codex-smoke":
        target = Path(args.project_root).resolve()
        cleanup_dir: tempfile.TemporaryDirectory[str] | None = None
        if str(target) == str(Path('.').resolve()):
            cleanup_dir = tempfile.TemporaryDirectory(prefix="agent-learner-smoke-")
            target = Path(cleanup_dir.name).resolve()
        install_codex_adapter(target)
        lifecycle = LearningLifecycle(target / ".codex" / "references" / "learning")
        lifecycle.promote(
            LearningRule(
                name="codex-hook-tests",
                rule="Update tests whenever the Codex prompt hook changes.",
                why="Prompt injection wiring should remain regression-tested.",
                scope="codex adapter",
                good_pattern="Change prompt hook code and tests together.",
                avoid_pattern="Ship prompt hook changes without verification.",
                summary="Keep Codex prompt hook changes covered by tests.",
                triggers=["hook", "tests", "prompt"],
                task_types=["cli", "prompt"],
                file_patterns=["src/**", "tests/**"],
                priority="high",
                confidence="high",
            )
        )
        script_path = target / ".codex" / "references" / "scripts" / "codex_prompt_context.py"
        env = dict(os.environ)
        env["PATH"] = f"{Path(sys.executable).parent}:{env.get('PATH', '')}"
        src_path = str(Path(__file__).resolve().parents[2])
        env["PYTHONPATH"] = f"{src_path}:{env.get('PYTHONPATH', '')}" if env.get("PYTHONPATH") else src_path
        result = subprocess.run(
            [sys.executable, str(script_path)],
            input=json.dumps(
                {
                    "hook_event_name": "UserPromptSubmit",
                    "prompt": args.prompt,
                    "cwd": str(target),
                }
            ),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        output = result.stdout.strip()
        payload = json.loads(output) if output else None
        print(
            json.dumps(
                {
                    "project_root": str(target),
                    "hook_script": str(script_path),
                    "returncode": result.returncode,
                    "payload": payload,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if cleanup_dir is not None:
            cleanup_dir.cleanup()
        return 0 if result.returncode == 0 else result.returncode

    if args.command == "render-codex-context":
        project_root = Path(args.project_root).resolve()
        if args.format == "hook-json":
            payload = build_codex_user_prompt_hook_output(
                project_root,
                args.prompt,
                scope=args.scope,
                task_type=args.task_type,
                file_paths=args.files,
                limit=args.limit,
                token_budget=args.token_budget,
            )
            if payload:
                print(json.dumps(payload, ensure_ascii=False))
            return 0
        if args.format == "json":
            text = render_codex_learning_context(
                project_root / ".codex" / "references" / "learning",
                args.prompt,
                scope=args.scope,
                task_type=args.task_type,
                file_paths=args.files,
                limit=args.limit,
                token_budget=args.token_budget,
            )
            print(json.dumps({"additional_context": text}, ensure_ascii=False, indent=2))
            return 0
        text = render_codex_learning_context(
            project_root / ".codex" / "references" / "learning",
            args.prompt,
            scope=args.scope,
            task_type=args.task_type,
            file_paths=args.files,
            limit=args.limit,
            token_budget=args.token_budget,
        )
        if text:
            print(text)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
