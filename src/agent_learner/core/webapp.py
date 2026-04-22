from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .brain import apply_candidate_action, promote_rule_to_global
from .dashboard import build_dashboard_summary


def render_dashboard_app_html(project_root: Path) -> str:
    project_root = project_root.resolve()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>agent-learner app</title>
  <style>
    :root {{
      --bg: #f7f2e8;
      --ink: #172126;
      --muted: #56636b;
      --panel: #fffaf1;
      --line: #d8cfbf;
      --accent: #0d6b5f;
      --accent2: #b85c38;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Georgia, serif; background: linear-gradient(180deg, #fbf7ef 0%, var(--bg) 100%); color: var(--ink); }}
    .wrap {{ max-width: 1240px; margin: 0 auto; padding: 28px 18px 60px; }}
    .hero, .panel {{ background: var(--panel); border: 1px solid var(--line); border-radius: 18px; box-shadow: 0 10px 30px rgba(23,33,38,0.06); }}
    .hero {{ padding: 24px; }}
    .panel {{ padding: 18px; margin-top: 18px; }}
    .meta {{ display: flex; gap: 14px; flex-wrap: wrap; color: var(--muted); margin-top: 10px; }}
    .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin-top: 18px; }}
    .metric {{ background: white; border: 1px solid var(--line); border-radius: 14px; padding: 14px; }}
    .metric span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }}
    .metric strong {{ display: block; margin-top: 8px; font-size: 28px; color: var(--accent); }}
    .split {{ display: grid; grid-template-columns: 1.15fr .85fr; gap: 18px; margin-top: 18px; }}
    .list, .cards {{ display: grid; gap: 12px; }}
    .rule, .candidate {{ background: white; border: 1px solid var(--line); border-radius: 14px; padding: 14px; }}
    .row {{ display: flex; justify-content: space-between; gap: 12px; align-items: center; }}
    .chips {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 8px; }}
    .chips span {{ border: 1px solid var(--line); border-radius: 999px; padding: 4px 8px; font-size: 12px; color: var(--muted); }}
    .actions {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }}
    button {{ border: 1px solid var(--line); background: white; border-radius: 999px; padding: 8px 12px; cursor: pointer; }}
    button.primary {{ background: var(--accent); border-color: var(--accent); color: white; }}
    button.warn {{ background: var(--accent2); border-color: var(--accent2); color: white; }}
    pre {{ white-space: pre-wrap; background: rgba(23,33,38,0.04); border-radius: 10px; padding: 10px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
    th, td {{ text-align: left; padding: 10px 8px; border-bottom: 1px solid rgba(216,207,191,0.65); vertical-align: top; }}
    th {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }}
    .toolbar {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 10px; }}
    .toggle.active {{ background: var(--accent); border-color: var(--accent); color: white; }}
    [data-scope-panel] {{ display: none; }}
    [data-scope-panel].active {{ display: block; }}
    .status {{ margin-top: 12px; color: var(--muted); }}
    @media (max-width: 980px) {{ .split {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>agent-learner app</h1>
      <p>Interactive local dashboard for local and global brain management.</p>
      <div class="meta">
        <span>project root: {project_root}</span>
      </div>
      <div class="metrics" id="metrics"></div>
      <div class="status" id="status">Loading summary...</div>
    </section>

    <div class="split">
      <section class="panel">
        <h2>Rules</h2>
        <div class="toolbar">
          <button class="toggle active" data-scope-toggle="merged">Merged</button>
          <button class="toggle" data-scope-toggle="local">Local</button>
          <button class="toggle" data-scope-toggle="global">Global</button>
        </div>
        <div class="cards active" id="rules-merged" data-scope-panel="merged"></div>
        <div class="cards" id="rules-local" data-scope-panel="local"></div>
        <div class="cards" id="rules-global" data-scope-panel="global"></div>
      </section>

      <section class="panel">
        <h2>Candidates</h2>
        <div class="cards" id="candidates"></div>
      </section>
    </div>

    <section class="panel">
      <h2>Recent History</h2>
      <table>
        <thead>
          <tr><th>Timestamp</th><th>Scope</th><th>Action</th><th>Rule</th><th>Decision</th><th>Reason</th></tr>
        </thead>
        <tbody id="history"></tbody>
      </table>
    </section>
  </div>

  <script>
    const statusEl = document.getElementById('status');
    const metricsEl = document.getElementById('metrics');
    const historyEl = document.getElementById('history');
    const ruleRoots = {{
      merged: document.getElementById('rules-merged'),
      local: document.getElementById('rules-local'),
      global: document.getElementById('rules-global'),
    }};
    const candidatesEl = document.getElementById('candidates');

    async function callApi(path, payload) {{
      const res = await fetch(path, {{
        method: 'POST',
        headers: {{ 'Content-Type': 'application/json' }},
        body: JSON.stringify(payload || {{}})
      }});
      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'request failed');
      return json;
    }}

    function renderMetric(label, value) {{
      return `<article class="metric"><span>${{label}}</span><strong>${{value}}</strong></article>`;
    }}

    function chips(items) {{
      return `<div class="chips">${{items.map((item) => `<span>${{item}}</span>`).join('')}}</div>`;
    }}

    function renderRuleCard(rule) {{
      const promote = rule.brain_scope === 'project'
        ? `<button class="primary" data-promote="${{rule.name}}">Promote Global</button>`
        : '';
      return `<article class="rule">
        <div class="row"><strong>${{rule.name}}</strong><span>${{rule.status}}</span></div>
        <p>${{rule.summary}}</p>
        ${{chips([rule.brain_scope, rule.scope, `uses ${{rule.use_count}}`])}}
        ${{rule.source_project ? `<div class="status">source project: ${{rule.source_project}}</div>` : ''}}
        ${{rule.related_rule ? `<div class="status">related: ${{rule.related_rule}}</div>` : ''}}
        <div class="actions">${{promote}}</div>
      </article>`;
    }}

    function renderCandidateCard(item) {{
      return `<article class="candidate">
        <div class="row"><strong>${{item.title}}</strong><span>${{item.status}}</span></div>
        <p>${{item.decision_reason || ''}}</p>
        ${{chips([item.adapter, item.decision || '-', item.confidence])}}
        ${{item.matched_rule ? `<div class="status">matched: ${{item.matched_rule}}</div>` : ''}}
        <pre>${{JSON.stringify(item.field_diffs || {{}}, null, 2)}}</pre>
        <div class="actions">
          <button class="primary" data-review="approve" data-candidate="${{item.path}}">Approve</button>
          <button data-review="needs-review" data-candidate="${{item.path}}">Needs Review</button>
          <button class="warn" data-review="reject" data-candidate="${{item.path}}">Reject</button>
        </div>
      </article>`;
    }}

    function bindActions() {{
      document.querySelectorAll('[data-promote]').forEach((button) => {{
        button.onclick = async () => {{
          try {{
            const result = await callApi('/api/promote-global', {{ name: button.dataset.promote }});
            statusEl.textContent = `Promoted globally: ${{result.rule}}`;
            await load();
          }} catch (err) {{
            statusEl.textContent = err.message;
          }}
        }};
      }});
      document.querySelectorAll('[data-review]').forEach((button) => {{
        button.onclick = async () => {{
          try {{
            const result = await callApi('/api/review-candidate', {{
              candidate: button.dataset.candidate,
              action: button.dataset.review
            }});
            statusEl.textContent = `Candidate action complete: ${{result.action}}`;
            await load();
          }} catch (err) {{
            statusEl.textContent = err.message;
          }}
        }};
      }});
    }}

    async function load() {{
      const res = await fetch('/api/summary');
      const summary = await res.json();
      metricsEl.innerHTML = [
        renderMetric('Local Rules', summary.overview.local_rules),
        renderMetric('Global Rules', summary.overview.global_rules),
        renderMetric('Merged Rules', summary.overview.merged_rules),
        renderMetric('Candidates', summary.overview.candidates),
        renderMetric('Local History', summary.overview.local_history_entries),
        renderMetric('Global History', summary.overview.global_history_entries),
      ].join('');

      ruleRoots.merged.innerHTML = (summary.merged.rules || []).map(renderRuleCard).join('') || '<p>No rules</p>';
      ruleRoots.local.innerHTML = (summary.local.rules || []).map(renderRuleCard).join('') || '<p>No rules</p>';
      ruleRoots.global.innerHTML = (summary.global.rules || []).map(renderRuleCard).join('') || '<p>No rules</p>';
      candidatesEl.innerHTML = (summary.candidates || []).map(renderCandidateCard).join('') || '<p>No candidates</p>';
      historyEl.innerHTML = (summary.recent_history || []).map((item) => `
        <tr>
          <td>${{item.ts || ''}}</td>
          <td>${{item.scope || ''}}</td>
          <td>${{item.action || ''}}</td>
          <td>${{item.rule || ''}}</td>
          <td>${{item.decision || ''}}</td>
          <td>${{item.reason || ''}}</td>
        </tr>
      `).join('') || '<tr><td colspan="6">No history</td></tr>';
      statusEl.textContent = `Loaded summary. Latest activity: ${{summary.overview.latest_activity || '-'}}`;
      bindActions();
    }}

    document.querySelectorAll('[data-scope-toggle]').forEach((button) => {{
      button.onclick = () => {{
        const target = button.dataset.scopeToggle;
        document.querySelectorAll('[data-scope-toggle]').forEach((b) => b.classList.toggle('active', b === button));
        document.querySelectorAll('[data-scope-panel]').forEach((panel) => panel.classList.toggle('active', panel.dataset.scopePanel === target));
      }};
    }});

    load().catch((err) => {{
      statusEl.textContent = err.message;
    }});
  </script>
</body>
</html>
"""


def apply_web_action(project_root: Path, action: str, payload: dict[str, object]) -> dict[str, object]:
    project_root = project_root.resolve()
    if action == "promote-global":
        name = str(payload.get("name") or "")
        if not name:
            raise ValueError("missing rule name")
        return promote_rule_to_global(project_root, name, all_projects=bool(payload.get("all_projects", False)))
    if action == "review-candidate":
        candidate = str(payload.get("candidate") or "")
        review_action = str(payload.get("action") or "")
        if not candidate or review_action not in {"approve", "reject", "needs-review"}:
            raise ValueError("invalid candidate action payload")
        return apply_candidate_action(project_root, candidate, review_action, reason=str(payload.get("reason") or "") or None)
    raise ValueError(f"unsupported action: {action}")


def run_dashboard_server(project_root: Path, host: str = "127.0.0.1", port: int = 8766) -> tuple[ThreadingHTTPServer, str]:
    project_root = project_root.resolve()
    html = render_dashboard_app_html(project_root)

    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict[str, object], status: int = 200) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, body: str) -> None:
            encoded = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

        def log_message(self, format: str, *args: object) -> None:
            return

        def do_GET(self) -> None:
            path = urlparse(self.path).path
            if path == "/":
                self._send_html(html)
                return
            if path == "/api/summary":
                self._send_json(build_dashboard_summary(project_root))
                return
            self._send_json({"error": "not found"}, status=404)

        def do_POST(self) -> None:
            path = urlparse(self.path).path
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_json({"error": "invalid json"}, status=400)
                return
            try:
                if path == "/api/promote-global":
                    result = apply_web_action(project_root, "promote-global", payload)
                elif path == "/api/review-candidate":
                    result = apply_web_action(project_root, "review-candidate", payload)
                else:
                    self._send_json({"error": "not found"}, status=404)
                    return
            except Exception as exc:  # pragma: no cover - defensive handler
                self._send_json({"error": str(exc)}, status=400)
                return
            self._send_json(result)

    server = ThreadingHTTPServer((host, port), Handler)
    return server, f"http://{host}:{server.server_address[1]}/"
