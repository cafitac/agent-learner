import React from "react";
import { CandidateRecord, HistoryRecord, RuleRecord, Summary, cardStyle, palette, panelStyle } from "./types";

const sectionTitleStyle: React.CSSProperties = {
  marginTop: 0,
  marginBottom: 14,
  fontSize: 24,
  letterSpacing: "-0.02em",
};

const mutedStyle: React.CSSProperties = {
  color: palette.textMuted,
};

const buttonBaseStyle: React.CSSProperties = {
  borderRadius: 999,
  padding: "10px 16px",
  border: `1px solid ${palette.lineStrong}`,
  background: "rgba(255,255,255,0.88)",
  color: palette.text,
  fontWeight: 600,
  letterSpacing: "-0.01em",
  cursor: "pointer",
  transition: "all 160ms ease",
};

function toneStyle(tone: "primary" | "danger" | "neutral"): React.CSSProperties {
  if (tone === "primary") {
    return { ...buttonBaseStyle, background: palette.blue, borderColor: palette.blue, color: "white", boxShadow: `0 10px 24px ${palette.blueSoft}` };
  }
  if (tone === "danger") {
    return { ...buttonBaseStyle, background: palette.red, borderColor: palette.red, color: "white", boxShadow: `0 10px 24px ${palette.redSoft}` };
  }
  return buttonBaseStyle;
}

function StatusPill({ text, tone = "neutral" }: { text: string; tone?: "neutral" | "success" | "warning" }) {
  const colors =
    tone === "success"
      ? { background: palette.greenSoft, color: palette.green, border: palette.greenSoft }
      : tone === "warning"
        ? { background: palette.redSoft, color: palette.red, border: palette.redSoft }
        : { background: "rgba(17,17,17,0.04)", color: palette.textMuted, border: "rgba(17,17,17,0.06)" };
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 6,
        padding: "6px 10px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 600,
        background: colors.background,
        color: colors.color,
        border: `1px solid ${colors.border}`,
      }}
    >
      {text}
    </span>
  );
}

function displayText(value: unknown, fallback: string) {
  const text = String(value ?? "").trim();
  return text ? text : fallback;
}

function candidateTone(status: string) {
  if (status === "approved" || status === "auto_applied") return "success";
  if (status === "needs_review" || status === "draft_candidate") return "warning";
  return "neutral";
}

function decisionTone(decision: string) {
  if (decision === "refresh_existing" || decision === "revise_existing" || decision === "new_rule") return "success";
  if (decision === "reject_candidate") return "warning";
  return "neutral";
}

export function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <article style={{ ...cardStyle, padding: 20 }}>
      <div style={{ fontSize: 12, textTransform: "uppercase", color: palette.textMuted, letterSpacing: "0.08em", fontWeight: 700 }}>{label}</div>
      <strong style={{ display: "block", fontSize: 34, marginTop: 10, color: palette.text, letterSpacing: "-0.04em" }}>{String(value)}</strong>
    </article>
  );
}

export function CountList({ title, data }: { title: string; data: Record<string, number> }) {
  return (
    <section style={panelStyle}>
      <h3 style={{ ...sectionTitleStyle, fontSize: 20 }}>{title}</h3>
      <div style={{ display: "grid", gap: 8 }}>
        {Object.entries(data).map(([key, count]) => (
          <div key={key} style={{ display: "flex", justifyContent: "space-between", borderBottom: `1px solid ${palette.line}`, paddingBottom: 8 }}>
            <span style={{ color: palette.textMuted }}>{key}</span>
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
            border: `1px solid ${palette.line}`,
            borderRadius: 999,
            padding: "6px 10px",
            fontSize: 12,
            fontWeight: 600,
            color: palette.textMuted,
            background: "rgba(17,17,17,0.03)",
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
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap", color: palette.textMuted, marginTop: 14 }}>
        <span>project: {summary.project.name ?? "-"}</span>
        <span>model: {summary.project.current_model ?? "-"}</span>
        <span>languages: {summary.project.languages.join(", ") || "-"}</span>
        <span>frameworks: {summary.project.frameworks.join(", ") || "-"}</span>
      </div>
      <div style={{ display: "flex", gap: 16, flexWrap: "wrap", marginTop: 12, alignItems: "center" }}>
        <label style={{ color: palette.textMuted, fontSize: 14 }}>
          project
          <select
            value={selectedProject}
            onChange={(event) => setSelectedProject(event.target.value)}
            style={{ marginLeft: 8, padding: "10px 12px", borderRadius: 14, border: `1px solid ${palette.lineStrong}`, background: "rgba(255,255,255,0.88)", color: palette.text }}
          >
            {summary.known_projects.map((project) => (
              <option key={project.root} value={project.root}>
                {project.name}
              </option>
            ))}
          </select>
        </label>
        <label style={{ color: palette.textMuted, fontSize: 14 }}>
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
  counts,
  onPromoteGlobal,
  selectedRuleName,
  onSelectRule,
  disabled = false,
}: {
  scope: "curated" | "drafts" | "local" | "global";
  setScope: (value: "curated" | "drafts" | "local" | "global") => void;
  rules: RuleRecord[];
  counts: Record<"curated" | "drafts" | "local" | "global", number>;
  onPromoteGlobal: (name: string) => void;
  selectedRuleName: string;
  onSelectRule: (name: string) => void;
  disabled?: boolean;
}) {
  const tabs: Array<{ key: "curated" | "drafts" | "local" | "global"; label: string }> = [
    { key: "curated", label: "Curated" },
    { key: "drafts", label: "Drafts" },
    { key: "local", label: "Local" },
    { key: "global", label: "Global" },
  ];

  const helperText =
    scope === "curated"
      ? "Curated surfaces the highest-signal reusable rules first and hides empty draft placeholders."
      : scope === "drafts"
        ? "Drafts collects unfinished or low-signal rules that still need curation before they become reliable guidance."
        : scope === "local"
          ? "Local shows everything stored for the current project, including unfinished work."
          : "Global shows shared learning that has been promoted for cross-project reuse.";

  return (
    <section style={panelStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <h2 style={sectionTitleStyle}>Rules</h2>
        <div style={{ display: "flex", gap: 8 }}>
          {tabs.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setScope(key)}
              style={{
                ...buttonBaseStyle,
                background: scope === key ? palette.text : "rgba(255,255,255,0.72)",
                borderColor: scope === key ? palette.text : palette.lineStrong,
                color: scope === key ? "white" : palette.text,
                opacity: disabled ? 0.6 : 1,
              }}
              disabled={disabled}
            >
              <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
                {label}
                <span style={{ padding: "2px 8px", borderRadius: 999, background: scope === key ? "rgba(255,255,255,0.16)" : "rgba(17,17,17,0.05)", fontSize: 12 }}>
                  {counts[key]}
                </span>
              </span>
            </button>
          ))}
        </div>
      </div>
      <p style={{ ...mutedStyle, marginTop: 0, marginBottom: 16, lineHeight: 1.6 }}>{helperText}</p>
      <div style={{ display: "grid", gap: 12 }}>
        {rules.length === 0 ? <p style={mutedStyle}>No rules available for this scope yet.</p> : null}
        {rules.map((rule) => (
          <article
            key={String(rule.name)}
            style={{
              ...cardStyle,
              outline: selectedRuleName === String(rule.name) ? `2px solid ${palette.blue}` : "none",
              cursor: "pointer",
            }}
            onClick={() => onSelectRule(String(rule.name))}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
              <strong>{String(rule.name)}</strong>
              <StatusPill text={displayText(rule.status, "draft")} tone={String(rule.status) === "approved" ? "success" : "neutral"} />
            </div>
            <p style={{ ...mutedStyle, lineHeight: 1.6 }}>{displayText(rule.summary, "No summary yet. This rule still needs curation.")}</p>
            <Chips
              items={[
                `scope ${String(rule.learning_scope)}`,
                `applies ${displayText(rule.scope, "unspecified")}`,
                `uses ${String(rule.use_count)}`,
                rule.source_project ? `project ${String(rule.source_project)}` : "",
              ].filter(Boolean)}
            />
            {rule.related_rule ? <div style={{ ...mutedStyle, marginTop: 10 }}>related: {String(rule.related_rule)}</div> : null}
            {rule.learning_scope === "project" ? (
              <div style={{ marginTop: 10 }}>
                <button
                  onClick={() => onPromoteGlobal(String(rule.name))}
                  style={{ ...toneStyle("primary"), opacity: disabled ? 0.6 : 1 }}
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
      <h2 style={sectionTitleStyle}>Rule Detail</h2>
      {!rule ? (
        <p style={mutedStyle}>Select a rule to inspect provenance, usage, and scope.</p>
      ) : (
        <article style={{ ...cardStyle, position: "sticky", top: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
            <strong>{String(rule.name)}</strong>
            <StatusPill text={displayText(rule.status, "draft")} tone={String(rule.status) === "approved" ? "success" : "neutral"} />
          </div>
          <p style={{ ...mutedStyle, lineHeight: 1.6 }}>{displayText(rule.summary, "No summary yet. This rule still needs curation.")}</p>
          <Chips
            items={[
              `scope ${String(rule.learning_scope)}`,
              `applies ${displayText(rule.scope, "unspecified")}`,
              `uses ${String(rule.use_count)}`,
              `promote ${String(rule.promote_count)}`,
              `refresh ${String(rule.refresh_count)}`,
            ]}
          />
          {rule.source_project ? <div style={{ ...mutedStyle, marginTop: 8 }}>source project: {String(rule.source_project)}</div> : null}
          {rule.related_rule ? <div style={{ ...mutedStyle, marginTop: 8 }}>related rule: {String(rule.related_rule)}</div> : null}
          {rule.supersedes ? <div style={{ ...mutedStyle, marginTop: 8 }}>supersedes: {String(rule.supersedes)}</div> : null}
          {rule.learning_scope === "project" ? (
            <div style={{ marginTop: 12 }}>
              <button
                onClick={() => onPromoteGlobal(String(rule.name))}
                style={{ ...toneStyle("primary"), opacity: disabled ? 0.6 : 1 }}
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
  const pendingCount = candidates.filter((candidate) => {
    const status = displayText(candidate.status, "draft_candidate");
    return status === "draft_candidate" || status === "needs_review";
  }).length;

  return (
    <section style={panelStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <h2 style={sectionTitleStyle}>Candidates</h2>
        <StatusPill text={`${pendingCount} pending`} tone={pendingCount > 0 ? "warning" : "success"} />
      </div>
      <p style={{ ...mutedStyle, marginTop: 0, marginBottom: 16, lineHeight: 1.6 }}>
        Candidates are unfinalized learning signals. Review them here before they become trusted reusable guidance.
      </p>
      <div style={{ display: "grid", gap: 12 }}>
        {candidates.length === 0 ? (
          <article style={{ ...cardStyle, padding: 22 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <strong style={{ fontSize: 18 }}>No candidates right now</strong>
              <p style={{ ...mutedStyle, margin: 0, lineHeight: 1.6 }}>
                When new learning is captured, draft candidates will appear here with confidence, matching rule hints, and review actions.
              </p>
            </div>
          </article>
        ) : null}
        {candidates.map((candidate) => (
          <article
            key={String(candidate.path)}
            style={{
              ...cardStyle,
              outline: selectedCandidatePath === String(candidate.path) ? `2px solid ${palette.blue}` : "none",
              cursor: "pointer",
            }}
            onClick={() => onSelectCandidate(String(candidate.path))}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
              <strong>{displayText(candidate.title, "Untitled candidate")}</strong>
              <StatusPill text={displayText(candidate.status, "draft_candidate")} tone={candidateTone(displayText(candidate.status, "draft_candidate"))} />
            </div>
            <p style={{ ...mutedStyle, lineHeight: 1.6 }}>{displayText(candidate.decision_reason, "Awaiting review or additional evidence.")}</p>
            <Chips
              items={[
                String(candidate.adapter),
                `decision ${displayText(candidate.decision, "pending")}`,
                String(candidate.confidence || "-"),
                candidate.matched_rule ? `matched ${String(candidate.matched_rule)}` : "",
              ].filter(Boolean)}
            />
            <div style={{ marginTop: 10 }}>
              <StatusPill text={displayText(candidate.decision, "pending")} tone={decisionTone(displayText(candidate.decision, ""))} />
            </div>
            <pre style={{ whiteSpace: "pre-wrap", background: "rgba(17,17,17,0.035)", padding: 12, borderRadius: 16, border: `1px solid ${palette.line}` }}>
              {JSON.stringify(candidate.field_diffs ?? {}, null, 2)}
            </pre>
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
              <button onClick={() => onReviewCandidate(String(candidate.path), "approve")} style={{ ...toneStyle("primary"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
                Approve
              </button>
              <button onClick={() => onReviewCandidate(String(candidate.path), "needs-review")} style={{ ...toneStyle("neutral"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
                Needs Review
              </button>
              <button onClick={() => onReviewCandidate(String(candidate.path), "reject")} style={{ ...toneStyle("danger"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
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
      <h2 style={sectionTitleStyle}>Candidate Detail</h2>
      {!candidate ? (
        <article style={{ ...cardStyle, padding: 22 }}>
          <strong style={{ fontSize: 18 }}>Pick a candidate to inspect</strong>
          <p style={{ ...mutedStyle, marginBottom: 0, lineHeight: 1.6 }}>
            The detail view shows the review rationale, matching rule hint, structured field diffs, and the exact decision actions you can take next.
          </p>
        </article>
      ) : (
        <article style={{ ...cardStyle, position: "sticky", top: 20 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
              <strong>{displayText(candidate.title, "Untitled candidate")}</strong>
              <StatusPill text={displayText(candidate.status, "draft_candidate")} tone={candidateTone(displayText(candidate.status, "draft_candidate"))} />
            </div>
          <p style={{ ...mutedStyle, lineHeight: 1.6 }}>{displayText(candidate.decision_reason, "Awaiting review or additional evidence.")}</p>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 8 }}>
            <StatusPill text={displayText(candidate.decision, "pending")} tone={decisionTone(displayText(candidate.decision, ""))} />
            {candidate.matched_rule ? <StatusPill text={`matched ${String(candidate.matched_rule)}`} /> : null}
          </div>
          <Chips
            items={[
              String(candidate.adapter),
              `decision ${displayText(candidate.decision, "pending")}`,
              String(candidate.confidence || "-"),
                candidate.matched_rule ? `matched ${String(candidate.matched_rule)}` : "",
              ].filter(Boolean)}
          />
          <pre style={{ whiteSpace: "pre-wrap", background: "rgba(17,17,17,0.035)", padding: 12, borderRadius: 16, border: `1px solid ${palette.line}` }}>
            {JSON.stringify(candidate.field_diffs ?? {}, null, 2)}
          </pre>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
            <button onClick={() => onReviewCandidate(String(candidate.path), "approve")} style={{ ...toneStyle("primary"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
              Approve
            </button>
            <button onClick={() => onReviewCandidate(String(candidate.path), "needs-review")} style={{ ...toneStyle("neutral"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
              Needs Review
            </button>
            <button onClick={() => onReviewCandidate(String(candidate.path), "reject")} style={{ ...toneStyle("danger"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
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
    <section style={{ ...panelStyle, marginTop: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <h2 style={sectionTitleStyle}>Recent History</h2>
        <input
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder="Filter history..."
          style={{ padding: "12px 14px", borderRadius: 14, border: `1px solid ${palette.lineStrong}`, minWidth: 240, background: "rgba(255,255,255,0.88)", color: palette.text }}
        />
      </div>
      <p style={{ ...mutedStyle, marginTop: 0, marginBottom: 18, lineHeight: 1.6 }}>
        History is shown as a lightweight activity timeline so recent promotions, revisions, and review decisions are easier to scan.
      </p>
      <div style={{ display: "grid", gap: 12 }}>
        {filtered.length === 0 ? (
          <article style={{ ...cardStyle, padding: 22 }}>
            <strong style={{ fontSize: 18 }}>No matching history</strong>
            <p style={{ ...mutedStyle, marginBottom: 0, lineHeight: 1.6 }}>
              Try a broader filter or keep using the dashboard until new review and promotion events are recorded.
            </p>
          </article>
        ) : (
          filtered.map((item, index) => (
            <article key={`${String(item.ts)}-${index}`} style={{ ...cardStyle, padding: 20 }}>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start" }}>
                <div style={{ display: "grid", gap: 8 }}>
                  <strong style={{ fontSize: 16 }}>{displayText(item.rule, "Unnamed rule")}</strong>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                    <StatusPill text={displayText(item.action, "event")} tone="success" />
                    <StatusPill text={displayText(item.scope, "project")} />
                    {item.decision ? <StatusPill text={displayText(item.decision, "decision")} tone={decisionTone(displayText(item.decision, ""))} /> : null}
                  </div>
                </div>
                <div style={{ ...mutedStyle, fontSize: 13, whiteSpace: "nowrap" }}>{displayText(item.ts, "-")}</div>
              </div>
              <div style={{ marginTop: 12, display: "grid", gap: 6 }}>
                <div style={{ ...mutedStyle, lineHeight: 1.6 }}>
                  {displayText(item.reason, "No additional reason recorded for this event.")}
                </div>
              </div>
            </article>
          ))
        )}
      </div>
    </section>
  );
}
