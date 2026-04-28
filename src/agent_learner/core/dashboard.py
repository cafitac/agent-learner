from __future__ import annotations

import json
from collections import Counter
from html import escape
from pathlib import Path

from .context import detect_context
from .lifecycle import LearningLifecycle
from .pipeline import list_candidate_paths, load_candidate_record
from .storage import agent_learner_home, global_history_path, global_learning_root, promotions_history_path, read_jsonl, read_project_registry, register_project, resolve_learning_root


def build_dashboard_summary(project_root: Path) -> dict[str, object]:
    project_root = project_root.resolve()
    register_project(project_root)
    context = detect_context(project_root)
    local_root = resolve_learning_root(project_root)
    global_root = global_learning_root()
    local_lifecycle = LearningLifecycle(local_root)
    global_lifecycle = LearningLifecycle(global_root)
    local_lifecycle.cleanup_drafts()
    global_lifecycle.cleanup_drafts()
    local_lifecycle.sweep_rules(current_model=context.current_model)
    global_lifecycle.sweep_rules(current_model=context.current_model)

    local_rules = collect_rules(local_root)
    global_rules = collect_rules(global_root)
    merged_rules = merge_rules(local_rules, global_rules)
    candidates = collect_candidates(project_root)
    local_history_path = promotions_history_path(project_root)
    canonical_history_path = global_history_path()
    local_history = attach_scope(read_jsonl(local_history_path), "project") if local_history_path.resolve() != canonical_history_path.resolve() else []
    global_history = attach_scope(read_jsonl(canonical_history_path), "global")
    combined_history = sorted(local_history + global_history, key=lambda item: str(item.get("ts") or ""), reverse=True)

    summary = {
        "project": {
            "name": context.project_name,
            "root": str(project_root),
            "languages": context.languages,
            "frameworks": context.frameworks,
            "current_model": context.current_model,
        },
        "paths": {
            "local_learning_root": str(local_root),
            "global_learning_root": str(global_root),
            "agent_learner_home": str(agent_learner_home()),
            "dashboard_dir": str(project_root / ".agent-learner" / "dashboard"),
        },
        "known_projects": read_project_registry(),
        "overview": {
            "local_rules": len(local_rules),
            "global_rules": len(global_rules),
            "merged_rules": len(merged_rules),
            "candidates": len(candidates),
            "local_history_entries": len(local_history),
            "global_history_entries": len(global_history),
            "latest_activity": combined_history[0]["ts"] if combined_history else "",
            **automation_metrics(combined_history, candidates),
            **automation_trends(combined_history, candidates),
        },
        "history_summary": {
            "by_action": count_by(combined_history, "action"),
            "by_adapter": count_by(combined_history, "source_adapter"),
            "by_decision": count_by(combined_history, "decision"),
        },
        "exception_summary": {
            "rule_reasons": summarize_rule_exceptions(local_rules, global_rules),
            "candidate_reasons": summarize_candidate_exceptions(candidates),
        },
        "local": {
            "status_counts": count_by(local_rules, "status"),
            "rules": local_rules,
        },
        "global": {
            "status_counts": count_by(global_rules, "status"),
            "rules": global_rules,
        },
        "merged": {
            "rules": merged_rules,
            "source_counts": dict(sorted(Counter(rule["learning_scope"] for rule in merged_rules).items())),
        },
        "candidates": candidates,
        "recent_history": combined_history[:20],
    }
    return summary


def collect_rules(root: Path) -> list[dict[str, object]]:
    if not root.exists():
        return []
    lifecycle = LearningLifecycle(root)
    global_root = global_learning_root().resolve()
    root_resolved = root.resolve()
    records: list[dict[str, object]] = []
    for rule in lifecycle.list_rules():
        display_scope = "global" if root_resolved == global_root else rule.learning_scope
        records.append(
            {
                "name": rule.name,
                "status": rule.status,
                "summary": (rule.summary or rule.rule or "").strip(),
                "scope": (rule.scope or "").strip(),
                "learning_scope": display_scope,
                "source_project": rule.source_project,
                "decision": rule.decision,
                "decision_reason": rule.decision_reason,
                "related_rule": rule.related_rule,
                "supersedes": rule.supersedes,
                "why": (rule.why or "").strip(),
                "good_pattern": (rule.good_pattern or "").strip(),
                "avoid_pattern": (rule.avoid_pattern or "").strip(),
                "source": rule.source,
                "evidence": rule.evidence,
                "evidence_excerpt": rule.evidence_excerpt,
                "source_adapter": rule.source_adapter,
                "source_event": rule.source_event,
                "derived_from_candidate": rule.derived_from_candidate,
                "updated_at": rule.updated_at,
                "last_used": rule.last_used,
                "promote_count": rule.promote_count,
                "refresh_count": rule.refresh_count,
                "use_count": rule.use_count,
            }
        )
    return sorted(records, key=lambda item: (item["name"], item["status"]))


def merge_rules(local_rules: list[dict[str, object]], global_rules: list[dict[str, object]]) -> list[dict[str, object]]:
    merged: dict[str, dict[str, object]] = {}
    for record in global_rules + local_rules:
        name = str(record["name"])
        existing = merged.get(name)
        if existing is None or _rule_sort_key(record) > _rule_sort_key(existing):
            merged[name] = record
    return sorted(merged.values(), key=lambda item: str(item["name"]))


def _status_rank(status: object) -> int:
    normalized = str(status).strip().strip('"').strip("'")
    order = {
        "approved": 4,
        "needs_review": 3,
        "draft": 2,
        "deprecated": 1,
    }
    return order.get(normalized, 0)


def _rule_completeness(record: dict[str, object]) -> int:
    score = 0
    if str(record.get("summary") or "").strip():
        score += 2
    if str(record.get("scope") or "").strip():
        score += 1
    if str(record.get("source_project") or "").strip():
        score += 1
    return score


def _rule_sort_key(record: dict[str, object]) -> tuple[int, int, int, int]:
    return (
        _status_rank(record.get("status")),
        _rule_completeness(record),
        int(record.get("use_count") or 0),
        1 if str(record.get("learning_scope") or "") == "project" else 0,
    )


def collect_candidates(project_root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for path in list_candidate_paths(project_root):
        record = load_candidate_record(path)
        records.append(
            {
                "path": str(path),
                "adapter": record.candidate.adapter,
                "status": record.status,
                "title": record.candidate.title,
                "decision": record.candidate.decision,
                "decision_reason": record.candidate.decision_reason,
                "matched_rule": record.candidate.matched_rule,
                "confidence": record.candidate.confidence,
                "field_diffs": record.candidate.field_diffs or {},
            }
        )
    return sorted(records, key=lambda item: str(item["title"]))


def attach_scope(entries: list[dict[str, object]], scope: str) -> list[dict[str, object]]:
    return [{**entry, "scope": scope} for entry in entries]


def count_by(records: list[dict[str, object]], field: str) -> dict[str, int]:
    counter = Counter(str(record.get(field) or "(empty)") for record in records)
    return dict(sorted(counter.items(), key=lambda item: (-item[1], item[0])))


def automation_metrics(history: list[dict[str, object]], candidates: list[dict[str, object]]) -> dict[str, object]:
    total_actions = len(history)
    auto_actions = sum(
        1
        for item in history
        if str(item.get("action") or "") in {"promote", "refresh", "revise"}
    )
    pending_candidates = sum(
        1
        for item in candidates
        if str(item.get("status") or "") in {"draft_candidate", "needs_review_candidate"}
    )
    auto_rate = round((auto_actions / total_actions) * 100, 1) if total_actions else 0.0
    exception_rate = round((pending_candidates / max(len(candidates), 1)) * 100, 1) if candidates else 0.0
    return {
        "automation_rate": auto_rate,
        "exception_rate": exception_rate,
        "auto_resolved_actions": auto_actions,
        "pending_review_candidates": pending_candidates,
    }


def automation_trends(history: list[dict[str, object]], candidates: list[dict[str, object]], *, recent_limit: int = 10) -> dict[str, object]:
    recent_history = history[:recent_limit]
    recent_total = len(recent_history)
    recent_auto = sum(
        1
        for item in recent_history
        if str(item.get("action") or "") in {"promote", "refresh", "revise"}
    )
    recent_auto_rate = round((recent_auto / recent_total) * 100, 1) if recent_total else 0.0
    recent_pending = sum(
        1
        for item in candidates[:recent_limit]
        if str(item.get("status") or "") in {"draft_candidate", "needs_review_candidate"}
    )
    recent_exception_rate = round((recent_pending / max(len(candidates[:recent_limit]), 1)) * 100, 1) if candidates[:recent_limit] else 0.0
    return {
        "recent_window": recent_limit,
        "recent_auto_rate": recent_auto_rate,
        "recent_exception_rate": recent_exception_rate,
        "recent_auto_resolved_actions": recent_auto,
        "recent_pending_review_candidates": recent_pending,
    }


def summarize_rule_exceptions(local_rules: list[dict[str, object]], global_rules: list[dict[str, object]]) -> dict[str, int]:
    rules = [rule for rule in [*local_rules, *global_rules] if str(rule.get("status") or "") == "needs_review"]
    deduped: dict[tuple[str, str, str], dict[str, object]] = {}
    for rule in rules:
        key = (
            str(rule.get("name") or ""),
            str(rule.get("status") or ""),
            str(rule.get("decision_reason") or rule.get("why") or ""),
        )
        deduped.setdefault(key, rule)
    reasons = [categorize_exception_reason(str(rule.get("decision_reason") or rule.get("why") or "")) for rule in deduped.values()]
    return dict(sorted(Counter(reasons).items(), key=lambda item: (-item[1], item[0])))


def summarize_candidate_exceptions(candidates: list[dict[str, object]]) -> dict[str, int]:
    unresolved = [candidate for candidate in candidates if str(candidate.get("status") or "").startswith("needs_review")]
    reasons = [categorize_exception_reason(str(candidate.get("decision_reason") or "")) for candidate in unresolved]
    return dict(sorted(Counter(reasons).items(), key=lambda item: (-item[1], item[0])))


def categorize_exception_reason(reason: str) -> str:
    normalized = (reason or "").lower()
    if not normalized.strip():
        return "other"
    if "model" in normalized:
        return "model-policy"
    if "conflict" in normalized or "negation" in normalized:
        return "conflict"
    if "fork" in normalized or "overlap" in normalized:
        return "overlap"
    if "revise" in normalized or "wording" in normalized or "materially" in normalized:
        return "wording-change"
    if "generic" in normalized or "too generic" in normalized:
        return "low-signal"
    if "scope" in normalized:
        return "scope-ambiguity"
    if "evidence" in normalized or "fresher evidence" in normalized:
        return "evidence"
    if "same conceptual rule" in normalized:
        return "wording-change"
    if "safe merge" in normalized:
        return "overlap"
    return "other"


def write_dashboard_files(project_root: Path) -> tuple[Path, Path]:
    summary = build_dashboard_summary(project_root)
    dashboard_dir = project_root / ".agent-learner" / "dashboard"
    dashboard_dir.mkdir(parents=True, exist_ok=True)
    json_path = dashboard_dir / "dashboard.json"
    html_path = dashboard_dir / "index.html"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    html_path.write_text(render_dashboard_html(summary), encoding="utf-8")
    return json_path, html_path


def render_dashboard_html(summary: dict[str, object]) -> str:
    project = summary["project"]
    overview = summary["overview"]
    local_status = summary["local"]["status_counts"]
    global_status = summary["global"]["status_counts"]
    merged_source = summary["merged"]["source_counts"]
    history_summary = summary["history_summary"]
    local_rules = summary["local"]["rules"]
    global_rules = summary["global"]["rules"]
    merged_rules = summary["merged"]["rules"]
    candidates = summary["candidates"]
    recent_history = summary["recent_history"]

    def render_counts(title: str, data: dict[str, int]) -> str:
        rows = "".join(f"<li><span>{escape(key)}</span><strong>{value}</strong></li>" for key, value in data.items()) or "<li><span>none</span><strong>0</strong></li>"
        return f"<section class='panel'><h3>{escape(title)}</h3><ul class='stats-list'>{rows}</ul></section>"

    cards = [
        ("Local Rules", overview["local_rules"]),
        ("Global Rules", overview["global_rules"]),
        ("Merged Rules", overview["merged_rules"]),
        ("Candidates", overview["candidates"]),
        ("Local History", overview["local_history_entries"]),
        ("Global History", overview["global_history_entries"]),
    ]
    card_html = "".join(
        f"<article class='metric'><span>{escape(label)}</span><strong>{value}</strong></article>"
        for label, value in cards
    )

    def render_rule_cards(items: list[dict[str, object]]) -> str:
        cards = "".join(
            "<article class='rule-card'>"
            f"<header><strong>{escape(str(item['name']))}</strong><span>{escape(str(item['status']))}</span></header>"
            f"<p>{escape(str(item['summary']))}</p>"
            f"<div class='chips'>"
            f"<span>{escape(str(item['learning_scope']))}</span>"
            f"<span>{escape(str(item['scope']))}</span>"
            f"<span>uses {escape(str(item['use_count']))}</span>"
            "</div>"
            + (f"<div class='meta-line'>related: {escape(str(item['related_rule']))}</div>" if item.get("related_rule") else "")
            + (f"<div class='meta-line'>source project: {escape(str(item['source_project']))}</div>" if item.get("source_project") else "")
            + "</article>"
            for item in items[:24]
        )
        return cards or "<p class='empty'>No rules</p>"

    candidate_rows = "".join(
        "<tr>"
        f"<td>{escape(item['title'])}</td>"
        f"<td>{escape(str(item['adapter']))}</td>"
        f"<td>{escape(str(item['status']))}</td>"
        f"<td>{escape(str(item['decision'] or '-'))}</td>"
        f"<td>{escape(str(item['matched_rule'] or '-'))}</td>"
        f"<td>{escape(str(item['confidence']))}</td>"
        "</tr>"
        for item in candidates[:20]
    ) or "<tr><td colspan='6'>No candidates</td></tr>"

    candidate_detail_cards = "".join(
        "<article class='candidate-card'>"
        f"<header><strong>{escape(str(item['title']))}</strong><span>{escape(str(item['status']))}</span></header>"
        f"<p>{escape(str(item['decision_reason'] or ''))}</p>"
        f"<div class='chips'><span>{escape(str(item['adapter']))}</span><span>{escape(str(item['decision'] or '-'))}</span><span>{escape(str(item['confidence']))}</span></div>"
        + (f"<div class='meta-line'>matched: {escape(str(item['matched_rule']))}</div>" if item.get("matched_rule") else "")
        + 
        f"<pre>{escape(json.dumps(item['field_diffs'], ensure_ascii=False, indent=2))}</pre>"
        "</article>"
        for item in candidates[:12]
    ) or "<p class='empty'>No candidate details</p>"

    history_rows = "".join(
        "<tr>"
        f"<td>{escape(str(item.get('ts') or ''))}</td>"
        f"<td>{escape(str(item.get('scope') or ''))}</td>"
        f"<td>{escape(str(item.get('action') or ''))}</td>"
        f"<td>{escape(str(item.get('rule') or ''))}</td>"
        f"<td>{escape(str(item.get('decision') or ''))}</td>"
        f"<td>{escape(str(item.get('reason') or ''))}</td>"
        "</tr>"
        for item in recent_history[:20]
    ) or "<tr><td colspan='6'>No history</td></tr>"

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>agent-learner dashboard</title>
  <style>
    :root {{
      --bg: #f5f1e8;
      --ink: #1f2a2e;
      --muted: #556268;
      --panel: #fffaf0;
      --line: #d8cdbd;
      --accent: #0d6b5f;
      --accent-2: #b85c38;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Iowan Old Style", serif;
      background:
        radial-gradient(circle at top left, rgba(184,92,56,0.12), transparent 32%),
        linear-gradient(180deg, #fbf7ef 0%, var(--bg) 100%);
      color: var(--ink);
    }}
    .wrap {{ max-width: 1200px; margin: 0 auto; padding: 32px 20px 64px; }}
    .hero {{
      border: 1px solid var(--line);
      background: linear-gradient(135deg, rgba(13,107,95,0.08), rgba(184,92,56,0.08)), var(--panel);
      padding: 24px;
      border-radius: 20px;
      box-shadow: 0 12px 40px rgba(31,42,46,0.08);
    }}
    h1, h2, h3 {{ margin: 0 0 12px; }}
    p {{ color: var(--muted); margin: 0; }}
    .meta {{ display: flex; flex-wrap: wrap; gap: 16px; margin-top: 12px; color: var(--muted); }}
    .metrics {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 14px;
      margin-top: 22px;
    }}
    .metric, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 16px;
    }}
    .metric span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .metric strong {{ display: block; margin-top: 8px; font-size: 30px; color: var(--accent); }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
      margin-top: 18px;
    }}
    .stats-list {{ list-style: none; padding: 0; margin: 0; }}
    .stats-list li {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(216,205,189,0.6); }}
    .stats-list li:last-child {{ border-bottom: 0; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      background: var(--panel);
      border-radius: 16px;
      overflow: hidden;
      border: 1px solid var(--line);
    }}
    th, td {{ text-align: left; padding: 12px 10px; border-bottom: 1px solid rgba(216,205,189,0.6); vertical-align: top; }}
    th {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); background: rgba(13,107,95,0.06); }}
    tr:last-child td {{ border-bottom: 0; }}
    .section {{ margin-top: 28px; }}
    .toolbar {{ display: flex; gap: 10px; flex-wrap: wrap; margin-top: 18px; }}
    .toggle {{
      border: 1px solid var(--line);
      background: white;
      color: var(--ink);
      border-radius: 999px;
      padding: 8px 14px;
      cursor: pointer;
    }}
    .toggle.active {{ background: var(--accent); color: white; border-color: var(--accent); }}
    .rule-grid, .candidate-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 14px;
      margin-top: 14px;
    }}
    .rule-card, .candidate-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 16px;
    }}
    .rule-card header, .candidate-card header {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 10px;
    }}
    .chips {{ display: flex; gap: 8px; flex-wrap: wrap; margin-top: 10px; }}
    .chips span {{
      font-size: 12px;
      color: var(--muted);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 4px 8px;
      background: rgba(13,107,95,0.04);
    }}
    .meta-line {{ margin-top: 8px; color: var(--muted); font-size: 13px; }}
    pre {{
      white-space: pre-wrap;
      font-size: 12px;
      background: rgba(31,42,46,0.04);
      border-radius: 12px;
      padding: 12px;
      overflow: auto;
    }}
    .empty {{ color: var(--muted); }}
    [data-scope-panel] {{ display: none; }}
    [data-scope-panel].active {{ display: block; }}
  </style>
</head>
<body>
  <div class="wrap">
    <section class="hero">
      <h1>agent-learner dashboard</h1>
      <p>Global learning first, project-aware drill-down.</p>
      <div class="meta">
        <span>project: {escape(str(project['name'] or '-'))}</span>
        <span>model: {escape(str(project['current_model'] or '-'))}</span>
        <span>languages: {escape(', '.join(project['languages']) or '-')}</span>
        <span>frameworks: {escape(', '.join(project['frameworks']) or '-')}</span>
        <span>latest activity: {escape(str(overview['latest_activity'] or '-'))}</span>
      </div>
      <div class="meta">
        <span>project root: {escape(str(project['root'] or '-'))}</span>
        <span>global learning home: {escape(str(summary['paths']['agent_learner_home']))}</span>
      </div>
      <div class="metrics">{card_html}</div>
    </section>

    <div class="grid">
      {render_counts("Local Status", local_status)}
      {render_counts("Global Status", global_status)}
      {render_counts("Merged Sources", merged_source)}
      {render_counts("History by Action", history_summary["by_action"])}
      {render_counts("History by Adapter", history_summary["by_adapter"])}
      {render_counts("History by Decision", history_summary["by_decision"])}
    </div>

    <section class="section">
      <h2>Rules</h2>
      <div class="toolbar">
        <button class="toggle active" data-scope-toggle="merged">Merged</button>
        <button class="toggle" data-scope-toggle="local">Local</button>
        <button class="toggle" data-scope-toggle="global">Global</button>
      </div>
      <div class="rule-grid active" data-scope-panel="merged">{render_rule_cards(merged_rules)}</div>
      <div class="rule-grid" data-scope-panel="local">{render_rule_cards(local_rules)}</div>
      <div class="rule-grid" data-scope-panel="global">{render_rule_cards(global_rules)}</div>
    </section>

    <section class="section">
      <h2>Candidates</h2>
      <table>
        <thead><tr><th>Title</th><th>Adapter</th><th>Status</th><th>Decision</th><th>Matched Rule</th><th>Confidence</th></tr></thead>
        <tbody>{candidate_rows}</tbody>
      </table>
      <div class="candidate-grid">{candidate_detail_cards}</div>
    </section>

    <section class="section">
      <h2>Recent History</h2>
      <table>
        <thead><tr><th>Timestamp</th><th>Scope</th><th>Action</th><th>Rule</th><th>Decision</th><th>Reason</th></tr></thead>
        <tbody>{history_rows}</tbody>
      </table>
    </section>
  </div>
  <script>
    const toggles = document.querySelectorAll('[data-scope-toggle]');
    const panels = document.querySelectorAll('[data-scope-panel]');
    toggles.forEach((button) => {{
      button.addEventListener('click', () => {{
        const target = button.getAttribute('data-scope-toggle');
        toggles.forEach((item) => item.classList.toggle('active', item === button));
        panels.forEach((panel) => panel.classList.toggle('active', panel.getAttribute('data-scope-panel') === target));
      }});
    }});
  </script>
</body>
</html>
"""
