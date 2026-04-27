from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import sys
import webbrowser
from pathlib import Path

from agent_learner.adapters import install_claude_adapter, install_codex_adapter, install_hermes_adapter
from agent_learner.adapters.claude import install_claude_adapter_with_scope
from agent_learner.adapters.codex import install_codex_adapter_with_scope
from agent_learner.adapters.hermes import install_hermes_adapter_with_scope
from agent_learner.adapters.codex_context import (
    build_codex_user_prompt_hook_output,
    format_retrieval_results_as_json,
    format_retrieval_results_as_text,
    render_codex_learning_context,
)
from agent_learner.core.global_learning import apply_candidate_action, promote_rule_to_global, sync_rules_to_global
from agent_learner.core.context import detect_context, write_current_model
from agent_learner.core.dashboard import build_dashboard_summary, write_dashboard_files
from agent_learner.core.doctor import collect_dashboard_doctor, ensure_frontend_dist, format_doctor_text
from agent_learner.core.indexing import rebuild_rule_index
from agent_learner.core.events import build_learning_event, write_learning_event
from agent_learner.core.pipeline import (
    list_candidate_paths,
    load_candidate_record,
    process_unprocessed_events,
    processed_results_as_json,
    processed_results_as_text,
)
from agent_learner.core.lifecycle import LearningLifecycle
from agent_learner.core.models import LearningRule
from agent_learner.core.storage import (
    ensure_global_learning_root,
    global_history_path,
    global_learning_root,
    promotions_history_path,
    read_jsonl,
    resolve_learning_root,
)
from agent_learner.core.webapp import run_dashboard_server


LEGACY_INSTALL_REPLACEMENTS = {
    "install-codex": "agent-learner bootstrap --adapters codex",
    "install-claude": "agent-learner bootstrap --adapters claude",
    "install-hermes": "agent-learner bootstrap --adapters hermes",
}


def filter_history_entries(entries: list[dict[str, object]], args: argparse.Namespace) -> list[dict[str, object]]:
    filtered = entries
    if getattr(args, "rule", None):
        filtered = [entry for entry in filtered if str(entry.get("rule") or "") == args.rule]
    if getattr(args, "action", None):
        filtered = [entry for entry in filtered if str(entry.get("action") or "") == args.action]
    if getattr(args, "decision", None):
        filtered = [entry for entry in filtered if str(entry.get("decision") or "") == args.decision]
    if getattr(args, "adapter", None):
        filtered = [entry for entry in filtered if str(entry.get("source_adapter") or "") == args.adapter]
    if getattr(args, "candidate", None):
        filtered = [entry for entry in filtered if str(entry.get("derived_from_candidate") or "") == args.candidate]
    if getattr(args, "since", None):
        filtered = [entry for entry in filtered if str(entry.get("ts") or "") >= args.since]
    if getattr(args, "until", None):
        filtered = [entry for entry in filtered if str(entry.get("ts") or "") <= args.until]
    filtered = sorted(filtered, key=lambda item: str(item.get("ts") or ""))
    if getattr(args, "latest_per_rule", False):
        latest: dict[str, dict[str, object]] = {}
        for entry in filtered:
            rule_key = str(entry.get("rule") or "")
            if not rule_key:
                continue
            current = latest.get(rule_key)
            if current is None or str(entry.get("ts") or "") >= str(current.get("ts") or ""):
                latest[rule_key] = entry
        filtered = sorted(latest.values(), key=lambda item: str(item.get("ts") or ""))
    if getattr(args, "last", None) is not None:
        filtered = filtered[-args.last :]
    if getattr(args, "limit", None) is not None:
        filtered = filtered[-args.limit :]
    return filtered


def emit_hermes_install_guidance(target: Path, *, scope: str, had_config: bool) -> None:
    hermes_root = target / ".hermes"
    snippet_path = hermes_root / "config.agent-learner.yaml"
    readme_path = hermes_root / "AGENT_LEARNER_README.md"
    if scope == "project":
        print("[agent-learner] Hermes adapter installed in project-local opt-in mode.", file=sys.stderr)
        if had_config:
            print(
                f"[agent-learner] Existing Hermes config preserved; review and merge {snippet_path} into the config you actually run.",
                file=sys.stderr,
            )
        else:
            print(
                f"[agent-learner] Project-local Hermes config created at {hermes_root / 'config.yaml'}.",
                file=sys.stderr,
            )
        print(f"[agent-learner] Safest activation: HERMES_HOME={hermes_root} hermes --accept-hooks", file=sys.stderr)
        print("[agent-learner] Project-local HERMES_HOME must also have model/auth configured; otherwise merge the snippet into your normal Hermes config instead.", file=sys.stderr)
        print(f"[agent-learner] Notes: {readme_path}", file=sys.stderr)
        return

    print("[agent-learner] Hermes user-scope hooks installed.", file=sys.stderr)
    if had_config:
        print(
            f"[agent-learner] Existing Hermes config preserved; review and merge {snippet_path} into your active Hermes config.",
            file=sys.stderr,
        )
    else:
        print(f"[agent-learner] Hermes config created at {hermes_root / 'config.yaml'}.", file=sys.stderr)
    print(f"[agent-learner] Notes: {readme_path}", file=sys.stderr)


def resolve_install_target(*, target: str | None, scope: str) -> Path:
    if target:
        return Path(target).expanduser().resolve()
    return Path.home() if scope == "user" else Path.cwd().resolve()


def exit_for_removed_install_command(parser: argparse.ArgumentParser, command: str) -> None:
    replacement = LEGACY_INSTALL_REPLACEMENTS[command]
    parser.exit(
        2,
        f"[agent-learner] Error: `{command}` was removed. Use `{replacement}` instead.\n",
    )


def emit_bootstrap_summary(*, adapters: list[str], used_default_target: bool, scopes: dict[str, str]) -> None:
    print(f"[agent-learner] Bootstrap installed adapters: {', '.join(adapters)}", file=sys.stderr)
    if used_default_target and all(scopes.get(adapter) == "user" for adapter in adapters):
        print(
            "[agent-learner] Default bootstrap keeps everything in user scope unless you opt into project scope.",
            file=sys.stderr,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agent-learner")
    sub = parser.add_subparsers(dest="command")

    init_cmd = sub.add_parser("init")
    init_cmd.add_argument("--root", default=".agent-learner")

    doctor_cmd = sub.add_parser("doctor")
    doctor_cmd.add_argument("--project-root", default=".")
    doctor_cmd.add_argument("--host", default="127.0.0.1")
    doctor_cmd.add_argument("--port", type=int, default=8766)
    doctor_cmd.add_argument("--format", choices=["text", "json"], default="text")

    dashboard_cmd = sub.add_parser("dashboard")
    dashboard_cmd.add_argument("--project-root", default=".")
    dashboard_cmd.add_argument("--host", default="127.0.0.1")
    dashboard_cmd.add_argument("--port", type=int, default=8766)
    dashboard_cmd.add_argument("--build", action="store_true")
    dashboard_cmd.add_argument("--no-build", action="store_true")
    dashboard_cmd.add_argument("--static", action="store_true")
    dashboard_cmd.add_argument("--open", action="store_true")

    bootstrap_cmd = sub.add_parser(
        "bootstrap",
        description="One-command setup: installs codex, claude, and hermes in user scope by default. Advanced flags are only needed for custom targets or project-local wiring.",
    )
    bootstrap_cmd.add_argument("--target", help="Advanced: override the default install root")
    bootstrap_cmd.add_argument(
        "--adapters",
        default="codex,claude,hermes",
        help="Advanced: limit bootstrap to a comma-separated subset such as hermes",
    )
    bootstrap_cmd.add_argument("--codex-scope", choices=["project", "user"], default="user", help="Advanced: override Codex install scope")
    bootstrap_cmd.add_argument("--claude-scope", choices=["project", "user"], default="user", help="Advanced: override Claude install scope")
    bootstrap_cmd.add_argument("--hermes-scope", choices=["project", "user"], default="user", help="Advanced: override Hermes install scope")

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

    promote_global_cmd = sub.add_parser("promote-global")
    promote_global_cmd.add_argument("--project-root", default=".")
    promote_global_cmd.add_argument("--name", required=True)
    promote_global_cmd.add_argument("--all-projects", action="store_true")
    promote_global_cmd.add_argument("--format", choices=["text", "json"], default="text")

    sync_global_cmd = sub.add_parser("sync-global")
    sync_global_cmd.add_argument("--project-root", default=".")
    sync_global_cmd.add_argument("--min-promote-count", type=int, default=1)
    sync_global_cmd.add_argument("--min-use-count", type=int, default=0)
    sync_global_cmd.add_argument("--all-projects", action="store_true")
    sync_global_cmd.add_argument("--format", choices=["text", "json"], default="text")

    sweep_cmd = sub.add_parser("sweep")
    sweep_cmd.add_argument("--project-root", default=".")
    sweep_cmd.add_argument("--unused-days", type=int, default=30)
    sweep_cmd.add_argument("--needs-review-days", type=int, default=30)
    sweep_cmd.add_argument("--format", choices=["text", "json"], default="text")

    rebuild_index_cmd = sub.add_parser("rebuild-index")
    rebuild_index_cmd.add_argument("--project-root", default=".")
    rebuild_index_cmd.add_argument("--scope", choices=["project", "global", "both"], default="both")
    rebuild_index_cmd.add_argument("--format", choices=["text", "json"], default="text")

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
    smoke_cmd.add_argument("--scope", choices=["project", "user"], default="project")

    claude_smoke_cmd = sub.add_parser("qa-claude-smoke")
    claude_smoke_cmd.add_argument("--project-root", default=".")

    hermes_smoke_cmd = sub.add_parser("qa-hermes-smoke")
    hermes_smoke_cmd.add_argument("--project-root", default=".")
    hermes_smoke_cmd.add_argument("--prompt", default="update hermes bootstrap wiring and keep tests green")

    capture_cmd = sub.add_parser("capture-event")
    capture_cmd.add_argument("--project-root", default=".")
    capture_cmd.add_argument("--adapter", required=True, choices=["codex", "claude", "hermes"])
    capture_cmd.add_argument("--event-name", required=True)
    capture_cmd.add_argument("--session-id")
    capture_cmd.add_argument("--transcript-path")

    process_cmd = sub.add_parser("process-events")
    process_cmd.add_argument("--project-root", default=".")
    process_cmd.add_argument("--adapter", choices=["codex", "claude", "hermes"])
    process_cmd.add_argument("--limit", type=int)
    process_cmd.add_argument("--format", choices=["text", "json"], default="text")

    review_candidates_cmd = sub.add_parser("review-candidates")
    review_candidates_cmd.add_argument("--project-root", default=".")
    review_candidates_cmd.add_argument("--adapter", choices=["codex", "claude", "hermes"])
    review_candidates_cmd.add_argument("--format", choices=["text", "json"], default="text")

    review_candidate_cmd = sub.add_parser("review-candidate")
    review_candidate_cmd.add_argument("--project-root", default=".")
    review_candidate_cmd.add_argument("--candidate", required=True)
    review_candidate_cmd.add_argument("--action", required=True, choices=["approve", "reject", "needs-review"])
    review_candidate_cmd.add_argument("--reason")
    review_candidate_cmd.add_argument("--format", choices=["text", "json"], default="text")

    history_cmd = sub.add_parser("history")
    history_cmd.add_argument("--project-root", default=".")
    history_cmd.add_argument("--rule")
    history_cmd.add_argument("--action")
    history_cmd.add_argument("--decision")
    history_cmd.add_argument("--adapter")
    history_cmd.add_argument("--candidate")
    history_cmd.add_argument("--since")
    history_cmd.add_argument("--until")
    history_cmd.add_argument("--last", type=int)
    history_cmd.add_argument("--latest-per-rule", action="store_true")
    history_cmd.add_argument("--limit", type=int)
    history_cmd.add_argument("--format", choices=["text", "json"], default="text")

    history_summary_cmd = sub.add_parser("history-summary")
    history_summary_cmd.add_argument("--project-root", default=".")
    history_summary_cmd.add_argument("--by", choices=["action", "rule", "adapter", "decision", "adapter-decision"], default="action")
    history_summary_cmd.add_argument("--rule")
    history_summary_cmd.add_argument("--action")
    history_summary_cmd.add_argument("--decision")
    history_summary_cmd.add_argument("--adapter")
    history_summary_cmd.add_argument("--candidate")
    history_summary_cmd.add_argument("--since")
    history_summary_cmd.add_argument("--until")
    history_summary_cmd.add_argument("--last", type=int)
    history_summary_cmd.add_argument("--latest-per-rule", action="store_true")
    history_summary_cmd.add_argument("--limit", type=int)
    history_summary_cmd.add_argument("--top", type=int)
    history_summary_cmd.add_argument("--format", choices=["text", "json"], default="text")
    overview_cmd = sub.add_parser("overview")
    overview_cmd.add_argument("--project-root", default=".")
    overview_cmd.add_argument("--since")
    overview_cmd.add_argument("--until")
    overview_cmd.add_argument("--last", type=int)
    overview_cmd.add_argument("--format", choices=["text", "json"], default="text")

    dashboard_summary_cmd = sub.add_parser("dashboard-summary")
    dashboard_summary_cmd.add_argument("--project-root", default=".")
    dashboard_summary_cmd.add_argument("--format", choices=["text", "json"], default="json")

    generate_dashboard_cmd = sub.add_parser("generate-dashboard")
    generate_dashboard_cmd.add_argument("--project-root", default=".")
    generate_dashboard_cmd.add_argument("--format", choices=["text", "json"], default="json")

    serve_dashboard_cmd = sub.add_parser("serve-dashboard")
    serve_dashboard_cmd.add_argument("--project-root", default=".")
    serve_dashboard_cmd.add_argument("--host", default="127.0.0.1")
    serve_dashboard_cmd.add_argument("--port", type=int, default=8766)

    serve_dashboard_fastapi_cmd = sub.add_parser("serve-dashboard-fastapi")
    serve_dashboard_fastapi_cmd.add_argument("--project-root", default=".")
    serve_dashboard_fastapi_cmd.add_argument("--host", default="127.0.0.1")
    serve_dashboard_fastapi_cmd.add_argument("--port", type=int, default=8766)

    context_cmd = sub.add_parser("render-codex-context")
    context_cmd.add_argument("--project-root", default=".")
    context_cmd.add_argument("--prompt", required=True)
    context_cmd.add_argument("--scope")
    context_cmd.add_argument("--task-type")
    context_cmd.add_argument("--file", action="append", dest="files", default=[])
    context_cmd.add_argument("--limit", type=int, default=3)
    context_cmd.add_argument("--token-budget", type=int, default=240)
    context_cmd.add_argument("--format", choices=["text", "json", "hook-json"], default="text")

    hermes_context_cmd = sub.add_parser("render-hermes-context")
    hermes_context_cmd.add_argument("--project-root", default=".")
    hermes_context_cmd.add_argument("--prompt", required=True)
    hermes_context_cmd.add_argument("--scope")
    hermes_context_cmd.add_argument("--task-type")
    hermes_context_cmd.add_argument("--file", action="append", dest="files", default=[])
    hermes_context_cmd.add_argument("--limit", type=int, default=3)
    hermes_context_cmd.add_argument("--token-budget", type=int, default=240)
    hermes_context_cmd.add_argument("--format", choices=["text", "json", "hook-json"], default="text")
    return parser


def main() -> int:
    parser = build_parser()
    raw_args = sys.argv[1:]
    if raw_args and raw_args[0] in LEGACY_INSTALL_REPLACEMENTS:
        exit_for_removed_install_command(parser, raw_args[0])
    args = parser.parse_args()
    if args.command == "init":
        lifecycle = LearningLifecycle(Path(args.root))
        print(f"initialized:{lifecycle.root}")
        return 0
    if args.command == "doctor":
        report = collect_dashboard_doctor(Path(args.project_root), host=args.host, port=args.port)
        if args.format == "json":
            print(json.dumps(report, ensure_ascii=False, indent=2))
        else:
            print(format_doctor_text(report))
        return 0
    if args.command == "dashboard":
        project_root = Path(args.project_root).resolve()
        report = collect_dashboard_doctor(project_root, host=args.host, port=args.port)
        if not report["port"]["ok"]:
            raise RuntimeError(f"Port {args.port} is already in use on {args.host}. Use `--port` to pick another one.")
        if args.static:
            json_path, html_path = write_dashboard_files(project_root)
            print(json.dumps({"json_path": str(json_path), "html_path": str(html_path)}, ensure_ascii=False))
            server, url = run_dashboard_server(project_root, host=args.host, port=args.port)
            print(url)
            if args.open:
                webbrowser.open(url)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0
        ensure_frontend_dist(project_root, build=(args.build or not args.no_build))
        from agent_learner.core.fastapi_app import create_fastapi_app

        app = create_fastapi_app(project_root)
        print(f"http://{args.host}:{args.port}/")
        if args.open:
            webbrowser.open(f"http://{args.host}:{args.port}/")
        try:
            import uvicorn
        except ModuleNotFoundError as exc:  # pragma: no cover
            raise RuntimeError("uvicorn is not installed. Install with `pip install .[web]` or `uv sync --extra web`.") from exc
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
        return 0
    if args.command == "bootstrap":
        adapters = [item.strip() for item in args.adapters.split(",") if item.strip()]
        written: list[Path] = []
        hermes_requested = "hermes" in adapters
        codex_target = resolve_install_target(target=args.target, scope=args.codex_scope)
        claude_target = resolve_install_target(target=args.target, scope=args.claude_scope)
        hermes_target = resolve_install_target(target=args.target, scope=args.hermes_scope)
        hermes_had_config = (hermes_target / ".hermes" / "config.yaml").exists() if hermes_requested else False
        if "codex" in adapters:
            written.extend(install_codex_adapter_with_scope(codex_target, scope=args.codex_scope))
        if "claude" in adapters:
            written.extend(install_claude_adapter_with_scope(claude_target, scope=args.claude_scope))
        if hermes_requested:
            written.extend(install_hermes_adapter_with_scope(hermes_target, scope=args.hermes_scope))
        for path in dict.fromkeys(written):
            print(path)
        emit_bootstrap_summary(
            adapters=adapters,
            used_default_target=args.target is None,
            scopes={
                "codex": args.codex_scope,
                "claude": args.claude_scope,
                "hermes": args.hermes_scope,
            },
        )
        if hermes_requested:
            emit_hermes_install_guidance(hermes_target, scope=args.hermes_scope, had_config=hermes_had_config)
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
        lifecycle = LearningLifecycle(resolve_learning_root(project_root))
        path = lifecycle.validate_rule(args.name, args.model)
        print(path)
        return 0
    if args.command == "exclude-rule":
        project_root = Path(args.project_root).resolve()
        lifecycle = LearningLifecycle(resolve_learning_root(project_root))
        path = lifecycle.exclude_rule(args.name, args.model)
        print(path)
        return 0
    if args.command == "promote-global":
        payload = promote_rule_to_global(Path(args.project_root), args.name, all_projects=args.all_projects)
        if args.format == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(payload, ensure_ascii=False))
        return 0
    if args.command == "sync-global":
        promoted = sync_rules_to_global(
            Path(args.project_root),
            min_promote_count=args.min_promote_count,
            min_use_count=args.min_use_count,
            all_projects=args.all_projects,
        )
        if args.format == "json":
            print(json.dumps(promoted, ensure_ascii=False, indent=2))
        else:
            if not promoted:
                print("No eligible rules promoted.")
            else:
                for item in promoted:
                    print(f"- {item['rule']} -> {item['path']}")
        return 0
    if args.command == "sweep":
        project_root = Path(args.project_root).resolve()
        lifecycle = LearningLifecycle(resolve_learning_root(project_root))
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
    if args.command == "rebuild-index":
        project_root = Path(args.project_root).resolve()
        payload: list[dict[str, object]] = []
        if args.scope in {"project", "both"}:
            lifecycle = LearningLifecycle(resolve_learning_root(project_root))
            payload.append({"scope": "project", **rebuild_rule_index(lifecycle)})
        if args.scope in {"global", "both"}:
            lifecycle = LearningLifecycle(ensure_global_learning_root())
            payload.append({"scope": "global", **rebuild_rule_index(lifecycle)})
        if args.format == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for item in payload:
                print(f"- {item['scope']}: {item['total_rules']} rules -> {item['json_path']}")
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

    if args.command == "review-candidates":
        project_root = Path(args.project_root).resolve()
        records = [load_candidate_record(path) for path in list_candidate_paths(project_root, adapter=args.adapter)]
        if args.format == "json":
            payload = [
                {
                    "path": str(record.path),
                    "adapter": record.candidate.adapter,
                    "status": record.status,
                    "title": record.candidate.title,
                    "summary": record.candidate.summary,
                    "decision": record.candidate.decision,
                    "decision_reason": record.candidate.decision_reason,
                    "confidence": record.candidate.confidence,
                    "matched_rule": record.candidate.matched_rule,
                    "review_required": record.candidate.review_required,
                    "field_diffs": record.candidate.field_diffs or {},
                }
                for record in records
            ]
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            if not records:
                print("No candidate files found.")
            else:
                for record in records:
                    print(
                        f"- {record.path.name} [{record.status}] adapter={record.candidate.adapter} "
                        f"decision={record.candidate.decision or 'none'} matched_rule={record.candidate.matched_rule or '-'} "
                        f"confidence={record.candidate.confidence}"
                    )
                    print(f"  summary={record.candidate.summary}")
                    if record.candidate.decision_reason:
                        print(f"  reason={record.candidate.decision_reason}")
                    if record.candidate.field_diffs:
                        print(f"  field_diffs={json.dumps(record.candidate.field_diffs, ensure_ascii=False)}")
        return 0

    if args.command == "review-candidate":
        payload = apply_candidate_action(Path(args.project_root), args.candidate, args.action, reason=args.reason)
        if args.format == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(payload, ensure_ascii=False))
        return 0

    if args.command == "history":
        project_root = Path(args.project_root).resolve()
        entries = filter_history_entries(read_jsonl(promotions_history_path(project_root)), args)
        if args.format == "json":
            print(json.dumps(entries, ensure_ascii=False, indent=2))
        else:
            if not entries:
                print("No history entries found.")
            else:
                for entry in entries:
                    print(
                        f"- {entry.get('ts','')} action={entry.get('action','')} rule={entry.get('rule','')} "
                        f"adapter={entry.get('source_adapter','')} decision={entry.get('decision','')} "
                        f"matched_rule={entry.get('matched_rule','')} reason={entry.get('reason','')}"
                    )
                    if entry.get("field_diffs_summary"):
                        print(f"  field_diffs={entry.get('field_diffs_summary')}")
        return 0

    if args.command == "history-summary":
        project_root = Path(args.project_root).resolve()
        entries = filter_history_entries(read_jsonl(promotions_history_path(project_root)), args)
        if args.by == "adapter-decision":
            matrix: dict[str, dict[str, int]] = {}
            for entry in entries:
                adapter = str(entry.get("source_adapter") or "(empty)")
                decision = str(entry.get("decision") or "(empty)")
                row = matrix.setdefault(adapter, {})
                row[decision] = row.get(decision, 0) + 1
            payload = {
                "group_by": args.by,
                "total_entries": len(entries),
                "matrix": matrix,
            }
            if args.format == "json":
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            else:
                if not matrix:
                    print("No history entries found.")
                else:
                    print(f"group_by={args.by} total_entries={len(entries)}")
                    for adapter, decisions in sorted(matrix.items()):
                        parts = [f"{decision}:{count}" for decision, count in sorted(decisions.items())]
                        print(f"- {adapter}: {', '.join(parts)}")
            return 0
        key_map = {
            "action": "action",
            "rule": "rule",
            "adapter": "source_adapter",
            "decision": "decision",
        }
        field = key_map[args.by]
        counts: dict[str, int] = {}
        for entry in entries:
            key = str(entry.get(field) or "")
            if not key:
                key = "(empty)"
            counts[key] = counts.get(key, 0) + 1
        summary = [{"key": key, "count": count} for key, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))]
        if args.top is not None:
            summary = summary[: args.top]
        if args.format == "json":
            print(json.dumps({"group_by": args.by, "total_entries": len(entries), "groups": summary}, ensure_ascii=False, indent=2))
        else:
            if not summary:
                print("No history entries found.")
            else:
                print(f"group_by={args.by} total_entries={len(entries)}")
                for item in summary:
                    print(f"- {item['key']}: {item['count']}")
        return 0

    if args.command == "overview":
        project_root = Path(args.project_root).resolve()
        entries = filter_history_entries(read_jsonl(promotions_history_path(project_root)), args)
        total_entries = len(entries)
        unique_rules = len({str(entry.get("rule") or "") for entry in entries if str(entry.get("rule") or "")})
        latest_ts = max((str(entry.get("ts") or "") for entry in entries), default="")

        def count_by(field: str) -> dict[str, int]:
            counts: dict[str, int] = {}
            for entry in entries:
                key = str(entry.get(field) or "(empty)")
                counts[key] = counts.get(key, 0) + 1
            return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))

        payload = {
            "total_entries": total_entries,
            "unique_rules": unique_rules,
            "latest_ts": latest_ts,
            "by_action": count_by("action"),
            "by_adapter": count_by("source_adapter"),
            "by_decision": count_by("decision"),
        }
        if args.format == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(f"total_entries={total_entries}")
            print(f"unique_rules={unique_rules}")
            print(f"latest_ts={latest_ts or '-'}")
            for label, counts in (
                ("by_action", payload["by_action"]),
                ("by_adapter", payload["by_adapter"]),
                ("by_decision", payload["by_decision"]),
            ):
                print(label)
                for key, count in counts.items():
                    print(f"- {key}: {count}")
        return 0

    if args.command == "dashboard-summary":
        project_root = Path(args.project_root).resolve()
        summary = build_dashboard_summary(project_root)
        if args.format == "json":
            print(json.dumps(summary, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(summary, ensure_ascii=False))
        return 0

    if args.command == "generate-dashboard":
        project_root = Path(args.project_root).resolve()
        json_path, html_path = write_dashboard_files(project_root)
        payload = {"json_path": str(json_path), "html_path": str(html_path)}
        if args.format == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(payload, ensure_ascii=False))
        return 0

    if args.command == "serve-dashboard":
        server, url = run_dashboard_server(Path(args.project_root), host=args.host, port=args.port)
        print(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0

    if args.command == "serve-dashboard-fastapi":
        from agent_learner.core.fastapi_app import create_fastapi_app

        app = create_fastapi_app(Path(args.project_root))
        print(f"http://{args.host}:{args.port}/")
        try:
            import uvicorn
        except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency gate
            raise RuntimeError("uvicorn is not installed. Install with `pip install .[web]` or `uv sync --extra web`.") from exc
        uvicorn.run(app, host=args.host, port=args.port, log_level="info")
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

    if args.command == "qa-hermes-smoke":
        target = Path(args.project_root).resolve()
        cleanup_dir: tempfile.TemporaryDirectory[str] | None = None
        if str(target) == str(Path('.').resolve()):
            cleanup_dir = tempfile.TemporaryDirectory(prefix="agent-learner-hermes-smoke-")
            target = Path(cleanup_dir.name).resolve()
        had_config_before_install = (target / ".hermes" / "config.yaml").exists()
        install_hermes_adapter(target)
        hermes_home = target / ".hermes"
        transcript_path = hermes_home / "sessions" / "session_hermes-smoke-session.jsonl"
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text(json.dumps({"message": "Always keep Hermes learning rules short and reusable."}) + "\n", encoding="utf-8")
        auto_script = hermes_home / "hooks" / "auto_session_learning.py"
        prompt_script = hermes_home / "hooks" / "hermes_prompt_context.py"
        lifecycle = LearningLifecycle(resolve_learning_root(target))
        lifecycle.promote(
            LearningRule(
                name="hermes-smoke-rule",
                rule="Keep Hermes bootstrap changes covered by tests.",
                why="Hermes adapter changes need regression coverage.",
                scope="hermes adapter",
                good_pattern="Update bootstrap code and tests together.",
                avoid_pattern="Change Hermes wiring without tests.",
                summary="Keep Hermes bootstrap changes covered by tests.",
                triggers=["hermes", "bootstrap", "tests"],
                task_types=["cli"],
                priority="high",
                confidence="high",
            )
        )
        env = dict(os.environ)
        env["PATH"] = f"{Path(sys.executable).parent}:{env.get('PATH', '')}"
        src_path = str(Path(__file__).resolve().parents[2])
        env["PYTHONPATH"] = f"{src_path}:{env.get('PYTHONPATH', '')}" if env.get("PYTHONPATH") else src_path
        env["HERMES_HOME"] = str(hermes_home)
        auto_result = subprocess.run(
            [sys.executable, str(auto_script)],
            input=json.dumps(
                {
                    "cwd": str(target),
                    "session_id": "hermes-smoke-session",
                    "extra": {
                        "summary": "Always keep Hermes learning rules short and reusable.",
                    },
                }
            ),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        prompt_result = subprocess.run(
            [sys.executable, str(prompt_script)],
            input=json.dumps(
                {
                    "cwd": str(target),
                    "session_id": "hermes-smoke-session",
                    "extra": {
                        "user_message": args.prompt,
                    },
                }
            ),
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )
        runtime: dict[str, object] = {"available": False}
        hermes_cli = shutil.which("hermes")
        if hermes_cli:
            runtime["available"] = True
            hooks_list = subprocess.run([hermes_cli, "hooks", "list"], capture_output=True, text=True, check=False, env=env, cwd=target)
            hooks_doctor = subprocess.run([hermes_cli, "hooks", "doctor"], capture_output=True, text=True, check=False, env=env, cwd=target)
            pre_payload_file = hermes_home / "pre_llm_payload.json"
            pre_payload_file.write_text(
                json.dumps({
                    "session_id": "hermes-smoke-session",
                    "cwd": str(target),
                    "user_message": args.prompt,
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            end_payload_file = hermes_home / "on_session_end_payload.json"
            end_payload_file.write_text(
                json.dumps({
                    "session_id": "hermes-smoke-session",
                    "cwd": str(target),
                    "summary": "Always keep Hermes learning rules short and reusable.",
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            hooks_test_pre = subprocess.run(
                [hermes_cli, "hooks", "test", "pre_llm_call", "--payload-file", str(pre_payload_file)],
                capture_output=True,
                text=True,
                check=False,
                env=env,
                cwd=target,
            )
            hooks_test_end = subprocess.run(
                [hermes_cli, "hooks", "test", "on_session_end", "--payload-file", str(end_payload_file)],
                capture_output=True,
                text=True,
                check=False,
                env=env,
                cwd=target,
            )
            runtime.update(
                {
                    "hooks_list_returncode": hooks_list.returncode,
                    "hooks_list_stdout": hooks_list.stdout.strip(),
                    "hooks_doctor_returncode": hooks_doctor.returncode,
                    "hooks_doctor_stdout": hooks_doctor.stdout.strip(),
                    "hooks_test_pre_returncode": hooks_test_pre.returncode,
                    "hooks_test_pre_stdout": hooks_test_pre.stdout.strip(),
                    "hooks_test_end_returncode": hooks_test_end.returncode,
                    "hooks_test_end_stdout": hooks_test_end.stdout.strip(),
                }
            )
        event_files = sorted((target / ".agent-learner" / "events" / "hermes").glob("*.json"))
        candidate_files = sorted((target / ".agent-learner" / "candidates" / "hermes").glob("*.md"))
        rule_files = sorted((target / ".agent-learner" / "learning" / "approved").glob("*.md"))
        prompt_payload = None
        prompt_stdout = prompt_result.stdout.strip()
        if prompt_stdout:
            try:
                prompt_payload = json.loads(prompt_stdout)
            except json.JSONDecodeError:
                prompt_payload = {"raw": prompt_stdout}
        activation_hint = f"HERMES_HOME={hermes_home} hermes --accept-hooks"
        merge_hint = f"Review and merge {hermes_home / 'config.agent-learner.yaml'} into the Hermes config you actually run if you already maintain one."
        config_created = not had_config_before_install
        config_preserved = had_config_before_install
        print(
            json.dumps(
                {
                    "project_root": str(target),
                    "hermes_home": str(hermes_home),
                    "config_path": str(hermes_home / "config.yaml"),
                    "config_created": config_created,
                    "config_preserved": config_preserved,
                    "activation_hint": activation_hint,
                    "merge_hint": merge_hint,
                    "auto_script": str(auto_script),
                    "prompt_script": str(prompt_script),
                    "auto_returncode": auto_result.returncode,
                    "prompt_returncode": prompt_result.returncode,
                    "event_files": [str(path) for path in event_files],
                    "candidate_files": [str(path) for path in candidate_files],
                    "rule_files": [str(path) for path in rule_files],
                    "prompt_payload": prompt_payload,
                    "runtime": runtime,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        if cleanup_dir is not None:
            cleanup_dir.cleanup()
        return 0 if auto_result.returncode == 0 and prompt_result.returncode == 0 else 1

    if args.command == "qa-codex-smoke":
        target = Path(args.project_root).resolve()
        cleanup_dir: tempfile.TemporaryDirectory[str] | None = None
        user_home_dir: tempfile.TemporaryDirectory[str] | None = None
        if str(target) == str(Path('.').resolve()):
            cleanup_dir = tempfile.TemporaryDirectory(prefix="agent-learner-smoke-")
            target = Path(cleanup_dir.name).resolve()
        if args.scope == "user":
            user_home_dir = tempfile.TemporaryDirectory(prefix="agent-learner-codex-user-home-")
            install_codex_adapter_with_scope(Path(user_home_dir.name).resolve(), scope="user")
            script_path = Path(user_home_dir.name).resolve() / ".codex" / "references" / "scripts" / "codex_prompt_context.py"
        else:
            install_codex_adapter(target)
            script_path = target / ".codex" / "references" / "scripts" / "codex_prompt_context.py"
        lifecycle = LearningLifecycle(resolve_learning_root(target))
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
        if user_home_dir is not None:
            user_home_dir.cleanup()
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
                resolve_learning_root(project_root),
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
            resolve_learning_root(project_root),
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
    if args.command == "render-hermes-context":
        project_root = Path(args.project_root).resolve()
        text = render_codex_learning_context(
            resolve_learning_root(project_root),
            args.prompt,
            scope=args.scope,
            task_type=args.task_type,
            file_paths=args.files,
            limit=args.limit,
            token_budget=args.token_budget,
        )
        if args.format == "hook-json":
            if text:
                print(json.dumps({"context": text}, ensure_ascii=False))
            return 0
        if args.format == "json":
            print(json.dumps({"additional_context": text}, ensure_ascii=False, indent=2))
            return 0
        if text:
            print(text)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
