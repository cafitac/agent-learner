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
|   `-- skills/
|-- .omx/
|   `-- wiki/
`-- .gitignore
```

The important guarantee is that Codex-only and Claude-only installs can be done independently.
