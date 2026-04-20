# Example Consumer Repo Layout

After running:

```bash
agent-learner bootstrap --target /path/to/consumer-repo
```

you should expect a consumer repo layout similar to:

```text
consumer-repo/
|-- .claude/
|   |-- hooks/
|   |-- settings.json
|   `-- skills/
|-- .codex/
|   |-- hooks.json
|   |-- references/
|   |   |-- learning/
|   |   `-- scripts/
|   `-- skills/
|-- .omx/
|   `-- wiki/
`-- .gitignore
```

The important guarantees are:
- Codex-only and Claude-only installs can be done independently
- approved Codex learning rules stay file-native under `.codex/references/learning/approved/`
- prompt-time context is injected ephemerally per task rather than appended to the persistent system prompt
