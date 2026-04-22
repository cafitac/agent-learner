import React, { useEffect, useRef } from "react";
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

const interactiveCardStyle: React.CSSProperties = {
  transition: "transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease",
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

export function StatusPill({ text, tone = "neutral" }: { text: string; tone?: "neutral" | "success" | "warning" }) {
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

function renderFieldDiffs(fieldDiffs: unknown) {
  const entries = Object.entries((fieldDiffs as Record<string, unknown>) || {});
  if (entries.length === 0) {
    return <p style={{ ...mutedStyle, margin: 0 }}>No structured field diffs recorded.</p>;
  }
  return (
    <div style={{ display: "grid", gap: 10 }}>
      {entries.map(([key, value]) => (
        <article key={key} style={{ ...cardStyle, padding: 14, boxShadow: "none" }}>
          <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>{key}</div>
          <div style={{ marginTop: 8, lineHeight: 1.7 }}>{displayText(value, "No value")}</div>
        </article>
      ))}
    </div>
  );
}

const RULE_DETAIL_MODAL_TITLE = "Rule Detail";
const CANDIDATE_DETAIL_MODAL_TITLE = "Candidate Detail";

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
  ruleFilter,
  setRuleFilter,
  onPromoteGlobal,
  onSelectRule,
  disabled = false,
}: {
  scope: "curated" | "drafts" | "local" | "global";
  setScope: (value: "curated" | "drafts" | "local" | "global") => void;
  rules: RuleRecord[];
  counts: Record<"curated" | "drafts" | "local" | "global", number>;
  ruleFilter: string;
  setRuleFilter: (value: string) => void;
  onPromoteGlobal: (name: string) => void;
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
      ? "Curated surfaces the highest-signal reusable rules first and hides unfinished draft noise."
      : scope === "drafts"
        ? "Drafts collects unfinished or low-signal rules that still need curation before they become reliable guidance."
        : scope === "local"
          ? "Local shows everything stored for the current project, including unfinished work."
          : "Global shows shared learning that has been promoted for cross-project reuse.";

  return (
    <section style={panelStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <h2 style={sectionTitleStyle}>Rules</h2>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
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
      <div style={{ marginBottom: 16 }}>
        <input
          value={ruleFilter}
          onChange={(event) => setRuleFilter(event.target.value)}
          placeholder="Filter rules by name, summary, scope, or rationale..."
          style={{ width: "100%", padding: "12px 14px", borderRadius: 14, border: `1px solid ${palette.lineStrong}`, background: "rgba(255,255,255,0.88)", color: palette.text }}
        />
      </div>
      <div style={{ display: "grid", gap: 12 }}>
        {rules.length === 0 ? <p style={mutedStyle}>No rules available for this scope yet.</p> : null}
        {rules.map((rule) => (
          <article
            key={String(rule.name)}
            style={{ ...cardStyle, ...interactiveCardStyle, cursor: "pointer" }}
            onClick={() => onSelectRule(String(rule.name))}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelectRule(String(rule.name));
              }
            }}
            tabIndex={0}
            role="button"
            aria-label={`Open details for rule ${String(rule.name)}`}
          >
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start" }}>
              <div>
                <strong>{String(rule.name)}</strong>
                <p style={{ ...mutedStyle, lineHeight: 1.6, marginBottom: 0 }}>{displayText(rule.summary, "No summary yet. This rule still needs curation.")}</p>
              </div>
              <StatusPill text={displayText(rule.status, "draft")} tone={String(rule.status) === "approved" ? "success" : "neutral"} />
            </div>
            <Chips
              items={[
                `scope ${String(rule.learning_scope)}`,
                `applies ${displayText(rule.scope, "unspecified")}`,
                `uses ${String(rule.use_count)}`,
                rule.source_project ? `project ${String(rule.source_project)}` : "",
              ].filter(Boolean)}
            />
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginTop: 12 }}>
              <span style={mutedStyle}>{displayText(rule.why, "Tap to inspect why, provenance, and rule details.")}</span>
              {rule.learning_scope === "project" ? (
                <button
                  onClick={(event) => {
                    event.stopPropagation();
                    onPromoteGlobal(String(rule.name));
                  }}
                  style={{ ...toneStyle("primary"), opacity: disabled ? 0.6 : 1 }}
                  disabled={disabled}
                >
                  Promote Global
                </button>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export function CandidatesPanel({
  candidates,
  onReviewCandidate,
  onSelectCandidate,
  disabled = false,
}: {
  candidates: CandidateRecord[];
  onReviewCandidate: (candidate: string, action: "approve" | "reject" | "needs-review") => void;
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
            style={{ ...cardStyle, ...interactiveCardStyle, cursor: "pointer" }}
            onClick={() => onSelectCandidate(String(candidate.path))}
            onKeyDown={(event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onSelectCandidate(String(candidate.path));
              }
            }}
            tabIndex={0}
            role="button"
            aria-label={`Open details for candidate ${displayText(candidate.title, "untitled candidate")}`}
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
            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 12 }}>
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  onReviewCandidate(String(candidate.path), "approve");
                }}
                style={{ ...toneStyle("primary"), opacity: disabled ? 0.6 : 1 }}
                disabled={disabled}
              >
                Approve
              </button>
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  onReviewCandidate(String(candidate.path), "needs-review");
                }}
                style={{ ...toneStyle("neutral"), opacity: disabled ? 0.6 : 1 }}
                disabled={disabled}
              >
                Needs Review
              </button>
              <button
                onClick={(event) => {
                  event.stopPropagation();
                  onReviewCandidate(String(candidate.path), "reject");
                }}
                style={{ ...toneStyle("danger"), opacity: disabled ? 0.6 : 1 }}
                disabled={disabled}
              >
                Reject
              </button>
            </div>
          </article>
        ))}
      </div>
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

export function DetailModal({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: React.ReactNode;
}) {
  const closeRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    closeRef.current?.focus();
  }, []);

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(17,17,17,0.38)",
        backdropFilter: "blur(12px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
        zIndex: 1000,
      }}
      aria-modal="true"
      role="dialog"
    >
      <div
        onClick={(event) => event.stopPropagation()}
        style={{
          width: "min(860px, 100%)",
          maxHeight: "min(86vh, 920px)",
          overflow: "auto",
          background: "rgba(255,255,255,0.92)",
          border: `1px solid ${palette.line}`,
          borderRadius: 28,
          boxShadow: palette.shadow,
          padding: 28,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 18 }}>
          <h2 style={{ ...sectionTitleStyle, marginBottom: 0 }}>{title}</h2>
          <button ref={closeRef} onClick={onClose} style={toneStyle("neutral")} aria-label={`Close ${title}`}>Close</button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function RuleModalContent({
  rule,
  onPromoteGlobal,
  disabled,
}: {
  rule: RuleRecord;
  onPromoteGlobal: (name: string) => void;
  disabled?: boolean;
}) {
  return (
    <div style={{ display: "grid", gap: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start" }}>
        <div>
          <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700, marginBottom: 8 }}>{RULE_DETAIL_MODAL_TITLE}</div>
          <strong style={{ fontSize: 22 }}>{String(rule.name)}</strong>
          <p style={{ ...mutedStyle, marginBottom: 0, lineHeight: 1.7 }}>{displayText(rule.summary, "No summary yet. This rule still needs curation.")}</p>
        </div>
        <StatusPill text={displayText(rule.status, "draft")} tone={String(rule.status) === "approved" ? "success" : "neutral"} />
      </div>

      <Chips
        items={[
          `scope ${String(rule.learning_scope)}`,
          `applies ${displayText(rule.scope, "unspecified")}`,
          `uses ${String(rule.use_count)}`,
          rule.source_project ? `project ${String(rule.source_project)}` : "",
        ].filter(Boolean)}
      />

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 18 }}>
        <article style={cardStyle}>
          <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>Why this exists</div>
          <p style={{ lineHeight: 1.7, marginBottom: 0 }}>{displayText(rule.why, "No rationale has been written yet.")}</p>
        </article>
        <article style={cardStyle}>
          <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>Good pattern</div>
          <p style={{ lineHeight: 1.7, marginBottom: 0 }}>{displayText(rule.good_pattern, "No good-pattern guidance recorded.")}</p>
        </article>
        <article style={cardStyle}>
          <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>Avoid</div>
          <p style={{ lineHeight: 1.7, marginBottom: 0 }}>{displayText(rule.avoid_pattern, "No avoid-pattern guidance recorded.")}</p>
        </article>
      </div>

      <article style={cardStyle}>
        <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700, marginBottom: 10 }}>Provenance</div>
        <div style={{ display: "grid", gap: 8 }}>
          {rule.decision_reason ? <div style={mutedStyle}>decision reason: {String(rule.decision_reason)}</div> : null}
          {rule.source_adapter ? <div style={mutedStyle}>source adapter: {String(rule.source_adapter)}</div> : null}
          {rule.source_event ? <div style={mutedStyle}>source event: {String(rule.source_event)}</div> : null}
          {rule.derived_from_candidate ? <div style={mutedStyle}>derived from: {String(rule.derived_from_candidate)}</div> : null}
          {rule.updated_at ? <div style={mutedStyle}>updated at: {String(rule.updated_at)}</div> : null}
          {rule.evidence_excerpt ? <div style={mutedStyle}>evidence excerpt: {String(rule.evidence_excerpt)}</div> : null}
          {rule.source ? <div style={mutedStyle}>source: {String(rule.source)}</div> : null}
          {rule.related_rule ? <div style={mutedStyle}>related rule: {String(rule.related_rule)}</div> : null}
          {rule.supersedes ? <div style={mutedStyle}>supersedes: {String(rule.supersedes)}</div> : null}
        </div>
      </article>

      {rule.learning_scope === "project" ? (
        <div>
          <button onClick={() => onPromoteGlobal(String(rule.name))} style={{ ...toneStyle("primary"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
            Promote Global
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function CandidateModalContent({
  candidate,
  onReviewCandidate,
  disabled,
}: {
  candidate: CandidateRecord;
  onReviewCandidate: (candidate: string, action: "approve" | "reject" | "needs-review") => void;
  disabled?: boolean;
}) {
  return (
    <div style={{ display: "grid", gap: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12 }}>
        <div>
          <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700, marginBottom: 8 }}>{CANDIDATE_DETAIL_MODAL_TITLE}</div>
          <strong style={{ fontSize: 22 }}>{displayText(candidate.title, "Untitled candidate")}</strong>
          <p style={{ ...mutedStyle, lineHeight: 1.7, marginBottom: 0 }}>{displayText(candidate.decision_reason, "Awaiting review or additional evidence.")}</p>
        </div>
        <StatusPill text={displayText(candidate.status, "draft_candidate")} tone={candidateTone(displayText(candidate.status, "draft_candidate"))} />
      </div>
      <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
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
      <article style={cardStyle}>
        <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700, marginBottom: 10 }}>Structured field diffs</div>
        {renderFieldDiffs(candidate.field_diffs)}
      </article>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button onClick={() => onReviewCandidate(String(candidate.path), "approve")} style={{ ...toneStyle("primary"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>Approve</button>
        <button onClick={() => onReviewCandidate(String(candidate.path), "needs-review")} style={{ ...toneStyle("neutral"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>Needs Review</button>
        <button onClick={() => onReviewCandidate(String(candidate.path), "reject")} style={{ ...toneStyle("danger"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>Reject</button>
      </div>
    </div>
  );
}
