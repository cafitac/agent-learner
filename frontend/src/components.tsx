import React from "react";
import { CandidateRecord, HistoryRecord, RuleRecord, Summary, cardStyle, panelStyle } from "./types";

export function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <article style={cardStyle}>
      <div style={{ fontSize: 12, textTransform: "uppercase", color: "#56636b", letterSpacing: "0.08em" }}>{label}</div>
      <strong style={{ display: "block", fontSize: 28, marginTop: 8, color: "#0d6b5f" }}>{String(value)}</strong>
    </article>
  );
}

export function CountList({ title, data }: { title: string; data: Record<string, number> }) {
  return (
    <section style={panelStyle}>
      <h3 style={{ marginTop: 0 }}>{title}</h3>
      <div style={{ display: "grid", gap: 8 }}>
        {Object.entries(data).map(([key, count]) => (
          <div key={key} style={{ display: "flex", justifyContent: "space-between", borderBottom: "1px solid rgba(216,207,191,0.6)", paddingBottom: 6 }}>
            <span style={{ color: "#56636b" }}>{key}</span>
            <strong>{count}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

export function Chips({ items }: { items: string[] }) {
  return (
    <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 8 }}>
      {items.map((item) => (
        <span
          key={item}
          style={{
            border: "1px solid #d8cfbf",
            borderRadius: 999,
            padding: "4px 8px",
            fontSize: 12,
            color: "#56636b",
            background: "rgba(13,107,95,0.04)",
          }}
        >
          {item}
        </span>
      ))}
    </div>
  );
}

export function ProjectSelector({
  summary,
  selectedProject,
  setSelectedProject,
  promoteAllProjects,
  setPromoteAllProjects,
}: {
  summary: Summary;
  selectedProject: string;
  setSelectedProject: (value: string) => void;
  promoteAllProjects: boolean;
  setPromoteAllProjects: (value: boolean) => void;
}) {
  return (
    <>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", color: "#56636b", marginTop: 12 }}>
        <span>project: {summary.project.name ?? "-"}</span>
        <span>model: {summary.project.current_model ?? "-"}</span>
        <span>languages: {summary.project.languages.join(", ") || "-"}</span>
        <span>frameworks: {summary.project.frameworks.join(", ") || "-"}</span>
      </div>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginTop: 12, alignItems: "center" }}>
        <label style={{ color: "#56636b", fontSize: 14 }}>
          project
          <select
            value={selectedProject}
            onChange={(event) => setSelectedProject(event.target.value)}
            style={{ marginLeft: 8, padding: "8px 10px", borderRadius: 10, border: "1px solid #d8cfbf" }}
          >
            {summary.known_projects.map((project) => (
              <option key={project.root} value={project.root}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
        <label style={{ color: "#56636b", fontSize: 14 }}>
          <input
            type="checkbox"
            checked={promoteAllProjects}
            onChange={(event) => setPromoteAllProjects(event.target.checked)}
            style={{ marginRight: 8 }}
          />
          Promote to all projects
        </label>
      </div>
    </>
  );
}

export function RulesPanel({
  scope,
  setScope,
  rules,
  onPromoteGlobal,
  selectedRuleName,
  onSelectRule,
  disabled = false,
}: {
  scope: "merged" | "local" | "global";
  setScope: (value: "merged" | "local" | "global") => void;
  rules: RuleRecord[];
  onPromoteGlobal: (name: string) => void;
  selectedRuleName: string;
  onSelectRule: (name: string) => void;
  disabled?: boolean;
}) {
  return (
    <section style={panelStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <h2 style={{ marginTop: 0 }}>Rules</h2>
        <div style={{ display: "flex", gap: 8 }}>
          {(["merged", "local", "global"] as const).map((key) => (
            <button
              key={key}
              onClick={() => setScope(key)}
              style={{
                borderRadius: 999,
                padding: "8px 12px",
                border: "1px solid #d8cfbf",
                background: scope === key ? "#0d6b5f" : "white",
                color: scope === key ? "white" : "#172126",
                opacity: disabled ? 0.6 : 1,
              }}
              disabled={disabled}
            >
              {key}
            </button>
          ))}
        </div>
      </div>
      <div style={{ display: "grid", gap: 12 }}>
        {rules.length === 0 ? <p style={{ color: "#56636b" }}>No rules available for this scope yet.</p> : null}
        {rules.map((rule) => (
          <article
            key={String(rule.name)}
            style={{
              ...cardStyle,
              outline: selectedRuleName === String(rule.name) ? "2px solid #0d6b5f" : "none",
              cursor: "pointer",
            }}
            onClick={() => onSelectRule(String(rule.name))}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
              <strong>{String(rule.name)}</strong>
              <span>{String(rule.status)}</span>
            </div>
            <p>{String(rule.summary)}</p>
            <Chips
              items={[
                `brain ${String(rule.brain_scope)}`,
                `scope ${String(rule.scope)}`,
                `uses ${String(rule.use_count)}`,
                rule.source_project ? `project ${String(rule.source_project)}` : "",
              ].filter(Boolean)}
            />
            {rule.related_rule ? <div style={{ color: "#56636b", marginTop: 8 }}>related: {String(rule.related_rule)}</div> : null}
            {rule.brain_scope === "project" ? (
              <div style={{ marginTop: 10 }}>
                <button
                  onClick={() => onPromoteGlobal(String(rule.name))}
                  style={{ borderRadius: 999, padding: "8px 12px", border: "1px solid #0d6b5f", background: "#0d6b5f", color: "white", opacity: disabled ? 0.6 : 1 }}
                  disabled={disabled}
                >
                  Promote Global
                </button>
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </section>
  );
}

export function RuleDetailPanel({
  rule,
  onPromoteGlobal,
  disabled = false,
}: {
  rule: RuleRecord | null;
  onPromoteGlobal: (name: string) => void;
  disabled?: boolean;
}) {
  return (
    <section style={panelStyle}>
      <h2 style={{ marginTop: 0 }}>Rule Detail</h2>
      {!rule ? (
        <p style={{ color: "#56636b" }}>Select a rule to inspect provenance, usage, and scope.</p>
      ) : (
        <article style={cardStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
            <strong>{String(rule.name)}</strong>
            <span>{String(rule.status)}</span>
          </div>
          <p>{String(rule.summary)}</p>
          <Chips
            items={[
              `brain ${String(rule.brain_scope)}`,
              `scope ${String(rule.scope)}`,
              `uses ${String(rule.use_count)}`,
              `promote ${String(rule.promote_count)}`,
              `refresh ${String(rule.refresh_count)}`,
            ]}
          />
          {rule.source_project ? <div style={{ color: "#56636b", marginTop: 8 }}>source project: {String(rule.source_project)}</div> : null}
          {rule.related_rule ? <div style={{ color: "#56636b", marginTop: 8 }}>related rule: {String(rule.related_rule)}</div> : null}
          {rule.supersedes ? <div style={{ color: "#56636b", marginTop: 8 }}>supersedes: {String(rule.supersedes)}</div> : null}
          {rule.brain_scope === "project" ? (
            <div style={{ marginTop: 12 }}>
              <button
                onClick={() => onPromoteGlobal(String(rule.name))}
                style={{ borderRadius: 999, padding: "8px 12px", border: "1px solid #0d6b5f", background: "#0d6b5f", color: "white", opacity: disabled ? 0.6 : 1 }}
                disabled={disabled}
              >
                Promote Global
              </button>
            </div>
          ) : null}
        </article>
      )}
    </section>
  );
}

export function CandidatesPanel({
  candidates,
  onReviewCandidate,
  selectedCandidatePath,
  onSelectCandidate,
  disabled = false,
}: {
  candidates: CandidateRecord[];
  onReviewCandidate: (candidate: string, action: "approve" | "reject" | "needs-review") => void;
  selectedCandidatePath: string;
  onSelectCandidate: (path: string) => void;
  disabled?: boolean;
}) {
  return (
    <section style={panelStyle}>
      <h2 style={{ marginTop: 0 }}>Candidates</h2>
      <div style={{ display: "grid", gap: 12 }}>
        {candidates.length === 0 ? <p style={{ color: "#56636b" }}>No candidate items available right now.</p> : null}
        {candidates.map((candidate) => (
          <article
            key={String(candidate.path)}
            style={{
              ...cardStyle,
              outline: selectedCandidatePath === String(candidate.path) ? "2px solid #b85c38" : "none",
              cursor: "pointer",
            }}
            onClick={() => onSelectCandidate(String(candidate.path))}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
              <strong>{String(candidate.title)}</strong>
              <span>{String(candidate.status)}</span>
            </div>
            <p>{String(candidate.decision_reason ?? "")}</p>
            <Chips
              items={[
                String(candidate.adapter),
                String(candidate.decision || "-"),
                String(candidate.confidence || "-"),
                candidate.matched_rule ? `matched ${String(candidate.matched_rule)}` : "",
              ].filter(Boolean)}
            />
            <pre style={{ whiteSpace: "pre-wrap", background: "rgba(23,33,38,0.04)", padding: 10, borderRadius: 10 }}>
              {JSON.stringify(candidate.field_diffs ?? {}, null, 2)}
            </pre>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
              <button onClick={() => onReviewCandidate(String(candidate.path), "approve")} style={{ borderRadius: 999, padding: "8px 12px", border: "1px solid #0d6b5f", background: "#0d6b5f", color: "white", opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
                Approve
              </button>
              <button onClick={() => onReviewCandidate(String(candidate.path), "needs-review")} style={{ borderRadius: 999, padding: "8px 12px", border: "1px solid #d8cfbf", background: "white", opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
                Needs Review
              </button>
              <button onClick={() => onReviewCandidate(String(candidate.path), "reject")} style={{ borderRadius: 999, padding: "8px 12px", border: "1px solid #b85c38", background: "#b85c38", color: "white", opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
                Reject
              </button>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export function CandidateDetailPanel({
  candidate,
  onReviewCandidate,
  disabled = false,
}: {
  candidate: CandidateRecord | null;
  onReviewCandidate: (candidate: string, action: "approve" | "reject" | "needs-review") => void;
  disabled?: boolean;
}) {
  return (
    <section style={panelStyle}>
      <h2 style={{ marginTop: 0 }}>Candidate Detail</h2>
      {!candidate ? (
        <p style={{ color: "#56636b" }}>Select a candidate to inspect matching rule, confidence, and field diffs.</p>
      ) : (
        <article style={cardStyle}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
            <strong>{String(candidate.title)}</strong>
            <span>{String(candidate.status)}</span>
          </div>
          <p>{String(candidate.decision_reason ?? "")}</p>
          <Chips
            items={[
              String(candidate.adapter),
              String(candidate.decision || "-"),
              String(candidate.confidence || "-"),
              candidate.matched_rule ? `matched ${String(candidate.matched_rule)}` : "",
            ].filter(Boolean)}
          />
          <pre style={{ whiteSpace: "pre-wrap", background: "rgba(23,33,38,0.04)", padding: 10, borderRadius: 10 }}>
            {JSON.stringify(candidate.field_diffs ?? {}, null, 2)}
          </pre>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
            <button onClick={() => onReviewCandidate(String(candidate.path), "approve")} style={{ borderRadius: 999, padding: "8px 12px", border: "1px solid #0d6b5f", background: "#0d6b5f", color: "white", opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
              Approve
            </button>
            <button onClick={() => onReviewCandidate(String(candidate.path), "needs-review")} style={{ borderRadius: 999, padding: "8px 12px", border: "1px solid #d8cfbf", background: "white", opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
              Needs Review
            </button>
            <button onClick={() => onReviewCandidate(String(candidate.path), "reject")} style={{ borderRadius: 999, padding: "8px 12px", border: "1px solid #b85c38", background: "#b85c38", color: "white", opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
              Reject
            </button>
          </div>
        </article>
      )}
    </section>
  );
}

export function HistoryTable({
  items,
  filter,
  setFilter,
}: {
  items: HistoryRecord[];
  filter: string;
  setFilter: (value: string) => void;
}) {
  const filtered = items.filter((item) => {
    const haystack = [item.ts, item.scope, item.action, item.rule, item.decision, item.reason].map((v) => String(v ?? "").toLowerCase()).join(" ");
    return haystack.includes(filter.toLowerCase());
  });
  return (
    <section style={{ ...panelStyle, marginTop: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <h2 style={{ marginTop: 0 }}>Recent History</h2>
        <input
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder="Filter history..."
          style={{ padding: "8px 10px", borderRadius: 10, border: "1px solid #d8cfbf", minWidth: 220 }}
        />
      </div>
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "10px 8px", color: "#56636b" }}>Timestamp</th>
              <th style={{ textAlign: "left", padding: "10px 8px", color: "#56636b" }}>Scope</th>
              <th style={{ textAlign: "left", padding: "10px 8px", color: "#56636b" }}>Action</th>
              <th style={{ textAlign: "left", padding: "10px 8px", color: "#56636b" }}>Rule</th>
              <th style={{ textAlign: "left", padding: "10px 8px", color: "#56636b" }}>Decision</th>
              <th style={{ textAlign: "left", padding: "10px 8px", color: "#56636b" }}>Reason</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td style={{ padding: "10px 8px", borderTop: "1px solid rgba(216,207,191,0.6)" }} colSpan={6}>
                  No history entries match the current filter.
                </td>
              </tr>
            ) : filtered.map((item, index) => (
              <tr key={`${String(item.ts)}-${index}`}>
                <td style={{ padding: "10px 8px", borderTop: "1px solid rgba(216,207,191,0.6)" }}>{String(item.ts ?? "")}</td>
                <td style={{ padding: "10px 8px", borderTop: "1px solid rgba(216,207,191,0.6)" }}>{String(item.scope ?? "")}</td>
                <td style={{ padding: "10px 8px", borderTop: "1px solid rgba(216,207,191,0.6)" }}>{String(item.action ?? "")}</td>
                <td style={{ padding: "10px 8px", borderTop: "1px solid rgba(216,207,191,0.6)" }}>{String(item.rule ?? "")}</td>
                <td style={{ padding: "10px 8px", borderTop: "1px solid rgba(216,207,191,0.6)" }}>{String(item.decision ?? "")}</td>
                <td style={{ padding: "10px 8px", borderTop: "1px solid rgba(216,207,191,0.6)" }}>{String(item.reason ?? "")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
