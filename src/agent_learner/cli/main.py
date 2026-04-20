from __future__ import annotations

import argparse
from pathlib import Path

from agent_learner.adapters import install_claude_adapter, install_codex_adapter
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
        written = []
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
        )
        path = lifecycle.promote(rule)
        print(path)
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
