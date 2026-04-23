import React, { useEffect, useRef } from "react";
import { CandidateRecord, HistoryRecord, RuleRecord, Summary, cardStyle, focusRingStyle, palette, panelStyle } from "./types";

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

function denseRowTemplate(compact = false) {
  return compact ? "minmax(0, 1fr)" : "minmax(0, 1.4fr) minmax(220px, 0.9fr) auto";
}

function historyRowTemplate(compact = false) {
  return compact ? "minmax(0, 1fr)" : "minmax(0, 1.2fr) minmax(220px, 0.9fr) auto";
}

function unresolvedReasonText(value: unknown) {
  const text = displayText(value, "");
  if (!text) return "The system could not safely finalize this item yet.";
  return text;
}

function useFocusRing() {
  const base = useRef<WeakMap<EventTarget & object, string>>(new WeakMap());
  const onFocus = (event: React.FocusEvent<HTMLElement>) => {
    const node = event.currentTarget;
    if (!base.current.has(node)) {
      base.current.set(node, node.style.boxShadow || "");
    }
    Object.assign(node.style, {
      outline: String(focusRingStyle.outline),
      outlineOffset: `${focusRingStyle.outlineOffset ?? 2}px`,
      boxShadow: String(focusRingStyle.boxShadow),
    });
  };
  const onBlur = (event: React.FocusEvent<HTMLElement>) => {
    const node = event.currentTarget;
    node.style.outline = "";
    node.style.outlineOffset = "";
    node.style.boxShadow = base.current.get(node) ?? "";
  };
  return { onFocus, onBlur };
}

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
        ? { background: palette.amberSoft, color: palette.amber, border: palette.amberSoft }
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

function formatDayLabel(value: unknown) {
  const text = displayText(value, "");
  if (!text) return "Unknown day";
  return text.split("T", 1)[0] || text;
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

function SectionBlock({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section style={{ display: "grid", gap: 10, paddingTop: 14, borderTop: `1px solid ${palette.line}` }}>
      <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>{title}</div>
      {children}
    </section>
  );
}

function KeyValueGrid({
  items,
}: {
  items: Array<{ label: string; value: string }>;
}) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
      {items.map((item) => (
        <article key={`${item.label}-${item.value}`} style={{ ...cardStyle, padding: 14, boxShadow: "none" }}>
          <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>{item.label}</div>
          <div style={{ marginTop: 8, lineHeight: 1.6 }}>{item.value}</div>
        </article>
      ))}
    </div>
  );
}

export function MetricCard({ label, value }: { label: string; value: string | number }) {
  return (
    <article style={{ ...cardStyle, padding: 20 }}>
      <div style={{ fontSize: 12, textTransform: "uppercase", color: palette.textMuted, letterSpacing: "0.08em", fontWeight: 700 }}>{label}</div>
      <strong style={{ display: "block", fontSize: 34, marginTop: 10, color: palette.text, letterSpacing: "-0.04em" }}>{String(value)}</strong>
    </article>
  );
}

export function StatStrip({
  items,
}: {
  items: Array<{ label: string; value: string | number }>;
}) {
  return (
    <section
      style={{
        ...panelStyle,
        padding: 16,
        borderRadius: 22,
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
        gap: 12,
      }}
    >
      {items.map((item) => (
        <div key={item.label} style={{ display: "grid", gap: 4 }}>
          <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>{item.label}</div>
          <div style={{ fontSize: 24, letterSpacing: "-0.03em", fontWeight: 700 }}>{String(item.value)}</div>
        </div>
      ))}
    </section>
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
  const focusHandlers = useFocusRing();
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
            onFocus={focusHandlers.onFocus}
            onBlur={focusHandlers.onBlur}
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
  compact = false,
}: {
  scope: "curated" | "needs_review" | "local" | "global";
  setScope: (value: "curated" | "needs_review" | "local" | "global") => void;
  rules: RuleRecord[];
  counts: Record<"curated" | "needs_review" | "local" | "global", number>;
  ruleFilter: string;
  setRuleFilter: (value: string) => void;
  onPromoteGlobal: (name: string) => void;
  onSelectRule: (name: string) => void;
  disabled?: boolean;
  compact?: boolean;
}) {
  const focusHandlers = useFocusRing();
  const tabs: Array<{ key: "curated" | "needs_review" | "local" | "global"; label: string }> = [
    { key: "curated", label: "Curated" },
    { key: "needs_review", label: "Needs Review" },
    { key: "local", label: "Local" },
    { key: "global", label: "Global" },
  ];

  const helperText =
    scope === "curated"
      ? "Curated surfaces the highest-signal reusable rules first and hides exception-queue noise."
      : scope === "needs_review"
        ? "Needs Review is the exception queue for rules the system could not safely finalize automatically."
        : scope === "local"
          ? "Local shows everything stored for the current project, including unfinished work."
          : "Global shows shared learning that has been promoted for cross-project reuse.";
  const sortHint =
    scope === "curated"
      ? "Sorted for quick reuse: strongest curated guidance first."
      : scope === "needs_review"
        ? "Sorted for exception handling: rules needing manual review first."
        : scope === "local"
          ? "Sorted by current project relevance before lower-signal leftovers."
          : "Sorted by shared reuse value across projects.";

  return (
    <section style={panelStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <h2 style={sectionTitleStyle}>Rules</h2>
        <div role="tablist" aria-label="Rule scopes" style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: "flex-end" }}>
          {tabs.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setScope(key)}
              role="tab"
              id={`rules-tab-${key}`}
              aria-controls={`rules-panel-${key}`}
              aria-selected={scope === key}
              onFocus={focusHandlers.onFocus}
              onBlur={focusHandlers.onBlur}
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
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        <StatusPill text={sortHint} />
        {scope === "needs_review" ? <StatusPill text="Open each item to see the unresolved reason and provenance before intervening." tone="warning" /> : null}
      </div>
      <div id={`rules-panel-${scope}`} role="tabpanel" aria-labelledby={`rules-tab-${scope}`} style={{ marginBottom: 16 }}>
        <input
          value={ruleFilter}
          onChange={(event) => setRuleFilter(event.target.value)}
          onFocus={focusHandlers.onFocus}
          onBlur={focusHandlers.onBlur}
          placeholder="Filter rules by name, summary, scope, or rationale..."
          style={{ width: "100%", padding: "12px 14px", borderRadius: 14, border: `1px solid ${palette.lineStrong}`, background: "rgba(255,255,255,0.88)", color: palette.text }}
        />
      </div>
      {rules.length > 0 ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: denseRowTemplate(compact),
            gap: 16,
            padding: "0 6px 10px",
            borderBottom: `1px solid ${palette.line}`,
            color: palette.textMuted,
            fontSize: 12,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
          }}
        >
          <div>Rule</div>
          <div>Rationale</div>
          <div style={{ textAlign: "right" }}>Status / Action</div>
        </div>
      ) : null}
      <div style={{ display: "grid", gap: 8 }}>
        {rules.length === 0 ? (
          <article style={{ ...cardStyle, padding: 22 }}>
            <strong style={{ display: "block", fontSize: 18 }}>
              {scope === "curated"
                ? "No curated rules yet"
                : scope === "needs_review"
                  ? "No rules need review"
                  : scope === "local"
                    ? "No local rules yet"
                    : "No global rules yet"}
            </strong>
            <p style={{ ...mutedStyle, marginBottom: 0, lineHeight: 1.6 }}>
              {scope === "curated"
                ? "Approved automation will populate the curated set as reusable guidance stabilizes."
                : scope === "needs_review"
                  ? "The exception queue is clear right now. Only ambiguous or low-confidence rules should appear here."
                  : scope === "local"
                    ? "This project has not stored any project-local rules yet."
                    : "No shared cross-project guidance has been promoted yet."}
            </p>
          </article>
        ) : null}
        {rules.map((rule) => (
          <article
            key={String(rule.name)}
            style={{
              background: "transparent",
              borderTop: `1px solid ${palette.line}`,
              padding: "18px 6px",
              ...interactiveCardStyle,
            }}
          >
            <div style={{ display: "grid", gridTemplateColumns: denseRowTemplate(compact), gap: 16, alignItems: "start" }}>
              <div style={{ minWidth: 0 }}>
                <strong style={{ display: "block", fontSize: 17, letterSpacing: "-0.02em" }}>{String(rule.name)}</strong>
                <p style={{ ...mutedStyle, lineHeight: 1.65, marginBottom: 0, marginTop: 6 }}>
                  {displayText(rule.summary, "No summary yet. This rule still needs curation.")}
                </p>
                {scope === "needs_review" ? (
                  <p style={{ marginTop: 10, marginBottom: 0, color: palette.amber, lineHeight: 1.6, fontSize: 13, fontWeight: 600 }}>
                    {unresolvedReasonText(rule.decision_reason || rule.why)}
                  </p>
                ) : null}
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ ...mutedStyle, fontSize: 13, lineHeight: 1.65 }}>
                  <strong style={{ color: palette.text, fontWeight: 600 }}>Why:</strong>{" "}
                  {displayText(rule.why, "Inspect the detail view for rationale and provenance.")}
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginTop: 10 }}>
                  <StatusPill text={displayText(rule.status, "needs_review")} tone={String(rule.status) === "approved" ? "success" : "warning"} />
                  <StatusPill text={displayText(rule.learning_scope, "project")} />
                  <StatusPill text={`uses ${String(rule.use_count ?? 0)}`} />
                </div>
              </div>
              <div style={{ display: "grid", justifyItems: compact ? "start" : "end", gap: 10 }}>
                <div style={{ ...mutedStyle, fontSize: 13, textAlign: compact ? "left" : "right" }}>
                  <div><strong style={{ color: palette.text, fontWeight: 600 }}>Applies:</strong> {displayText(rule.scope, "unspecified")}</div>
                  {rule.source_project ? <div>{`project ${String(rule.source_project)}`}</div> : null}
                </div>
                {rule.learning_scope === "project" ? (
                  <button
                    onClick={() => onPromoteGlobal(String(rule.name))}
                    onFocus={focusHandlers.onFocus}
                    onBlur={focusHandlers.onBlur}
                    style={{ ...toneStyle("primary"), opacity: disabled ? 0.6 : 1 }}
                    disabled={disabled}
                  >
                    Promote
                  </button>
                ) : null}
                <button onClick={() => onSelectRule(String(rule.name))} onFocus={focusHandlers.onFocus} onBlur={focusHandlers.onBlur} style={{ ...toneStyle("neutral"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
                  View details
                </button>
              </div>
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
  compact = false,
}: {
  candidates: CandidateRecord[];
  onReviewCandidate: (candidate: string, action: "approve" | "reject" | "needs-review") => void;
  onSelectCandidate: (path: string) => void;
  disabled?: boolean;
  compact?: boolean;
}) {
  const focusHandlers = useFocusRing();
  const pendingCount = candidates.filter((candidate) => {
    const status = displayText(candidate.status, "draft_candidate");
    return status === "draft_candidate" || status === "needs_review";
  }).length;
  const sortedCandidates = [...candidates].sort((a, b) => {
    const statusRank = (value: unknown) => {
      const status = displayText(value, "draft_candidate");
      if (status === "needs_review") return 3;
      if (status === "draft_candidate") return 2;
      if (status === "auto_applied" || status === "approved") return 1;
      return 0;
    };
    const confidenceRank = (value: unknown) => {
      const text = displayText(value, "-");
      if (text === "high") return 3;
      if (text === "medium") return 2;
      if (text === "low") return 1;
      return 0;
    };
    return (
      statusRank(b.status) - statusRank(a.status) ||
      confidenceRank(b.confidence) - confidenceRank(a.confidence) ||
      displayText(a.title, "").localeCompare(displayText(b.title, ""))
    );
  });

  return (
    <section style={panelStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <h2 style={sectionTitleStyle}>Candidates</h2>
        <StatusPill text={`${pendingCount} pending`} tone={pendingCount > 0 ? "warning" : "success"} />
      </div>
      <p style={{ ...mutedStyle, marginTop: 0, marginBottom: 16, lineHeight: 1.6 }}>
        Candidates are unfinalized learning signals. Review them here before they become trusted reusable guidance.
      </p>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 16 }}>
        <StatusPill text="Sorted by review urgency, then confidence, then title." />
        <StatusPill text="Open details to see why an item stayed in review instead of auto-applying." tone="warning" />
      </div>
      {candidates.length > 0 ? (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: denseRowTemplate(compact),
            gap: 16,
            padding: "0 6px 10px",
            borderBottom: `1px solid ${palette.line}`,
            color: palette.textMuted,
            fontSize: 12,
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: "0.08em",
          }}
        >
          <div>Candidate</div>
          <div>Review State</div>
          <div style={{ textAlign: "right" }}>Priority / Action</div>
        </div>
      ) : null}
      <div style={{ display: "grid", gap: 12 }}>
        {candidates.length === 0 ? (
          <article style={{ ...cardStyle, padding: 22 }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <strong style={{ fontSize: 18 }}>No candidates right now</strong>
              <p style={{ ...mutedStyle, margin: 0, lineHeight: 1.6 }}>
                When new learning is captured, candidates will appear here with confidence, matching rule hints, and review actions.
              </p>
              <p style={{ ...mutedStyle, margin: 0, lineHeight: 1.6 }}>
                If this stays empty in a fresh workspace, run real work through the learning adapter first so reviewable candidates can be captured.
              </p>
            </div>
          </article>
        ) : null}
        {sortedCandidates.map((candidate) => (
          <article
            key={String(candidate.path)}
            style={{
              background: "transparent",
              borderTop: `1px solid ${palette.line}`,
              padding: "18px 6px",
              ...interactiveCardStyle,
            }}
          >
            <div style={{ display: "grid", gridTemplateColumns: denseRowTemplate(compact), gap: 16, alignItems: "start" }}>
              <div style={{ minWidth: 0 }}>
                <strong style={{ display: "block", fontSize: 17, letterSpacing: "-0.02em" }}>{displayText(candidate.title, "Untitled candidate")}</strong>
                <p style={{ ...mutedStyle, lineHeight: 1.65, marginBottom: 0, marginTop: 6 }}>
                  {displayText(candidate.decision_reason, "Awaiting review or additional evidence.")}
                </p>
              </div>
              <div style={{ minWidth: 0 }}>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <StatusPill text={displayText(candidate.status, "draft_candidate")} tone={candidateTone(displayText(candidate.status, "draft_candidate"))} />
                  <StatusPill text={displayText(candidate.decision, "pending")} tone={decisionTone(displayText(candidate.decision, ""))} />
                  <StatusPill text={`confidence ${String(candidate.confidence || "-")}`} />
                </div>
                <div style={{ ...mutedStyle, marginTop: 10, lineHeight: 1.65 }}>
                  {candidate.matched_rule ? `Matched rule: ${String(candidate.matched_rule)}` : "No matched rule yet."}
                </div>
              </div>
              <div style={{ display: "grid", justifyItems: compact ? "start" : "end", gap: 10 }}>
                <div style={{ ...mutedStyle, fontSize: 13, textAlign: compact ? "left" : "right" }}>
                  <div>{String(candidate.adapter)}</div>
                </div>
                <div style={{ display: "flex", gap: 8, flexWrap: "wrap", justifyContent: compact ? "flex-start" : "flex-end" }}>
                  <button
                    onClick={(event) => {
                      onReviewCandidate(String(candidate.path), "approve");
                    }}
                    onFocus={focusHandlers.onFocus}
                    onBlur={focusHandlers.onBlur}
                    style={{ ...toneStyle("primary"), opacity: disabled ? 0.6 : 1 }}
                    disabled={disabled}
                  >
                    Approve
                  </button>
                  <button
                    onClick={(event) => {
                      onReviewCandidate(String(candidate.path), "needs-review");
                    }}
                    onFocus={focusHandlers.onFocus}
                    onBlur={focusHandlers.onBlur}
                    style={{ ...toneStyle("neutral"), opacity: disabled ? 0.6 : 1 }}
                    disabled={disabled}
                  >
                    Review
                  </button>
                  <button onClick={() => onSelectCandidate(String(candidate.path))} onFocus={focusHandlers.onFocus} onBlur={focusHandlers.onBlur} style={{ ...toneStyle("neutral"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
                    View details
                  </button>
                </div>
              </div>
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
  compact = false,
}: {
  items: HistoryRecord[];
  filter: string;
  setFilter: (value: string) => void;
  compact?: boolean;
}) {
  const focusHandlers = useFocusRing();
  const filtered = items.filter((item) => {
    const haystack = [item.ts, item.scope, item.action, item.rule, item.decision, item.reason].map((v) => String(v ?? "").toLowerCase()).join(" ");
    return haystack.includes(filter.toLowerCase());
  });
  const grouped = filtered.reduce<Record<string, HistoryRecord[]>>((acc, item) => {
    const key = formatDayLabel(item.ts);
    acc[key] ??= [];
    acc[key].push(item);
    return acc;
  }, {});
  return (
    <section style={{ ...panelStyle, marginTop: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
        <h2 style={sectionTitleStyle}>Recent History</h2>
        <input
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          onFocus={focusHandlers.onFocus}
          onBlur={focusHandlers.onBlur}
          placeholder="Filter history..."
          style={{ padding: "12px 14px", borderRadius: 14, border: `1px solid ${palette.lineStrong}`, minWidth: 240, background: "rgba(255,255,255,0.88)", color: palette.text }}
        />
      </div>
      <p style={{ ...mutedStyle, marginTop: 0, marginBottom: 18, lineHeight: 1.6 }}>
        History is shown as a lightweight activity timeline so recent promotions, revisions, and review decisions are easier to scan.
      </p>
      <div style={{ display: "grid", gap: 16 }}>
        {filtered.length === 0 ? (
          <article style={{ ...cardStyle, padding: 22 }}>
            <strong style={{ fontSize: 18 }}>No matching history</strong>
            <p style={{ ...mutedStyle, marginBottom: 0, lineHeight: 1.6 }}>
              Try a broader filter or keep using the dashboard until new review and promotion events are recorded.
            </p>
            {!filter.trim() ? (
              <p style={{ ...mutedStyle, marginBottom: 0, lineHeight: 1.6 }}>
                Fresh workspaces often stay empty here until the first promotion, revision, or candidate review is completed.
              </p>
            ) : null}
          </article>
        ) : (
          Object.entries(grouped).map(([day, dayItems]) => (
            <section key={day} style={{ display: "grid", gap: 4 }}>
              <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700, padding: "0 6px" }}>
                {day}
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: historyRowTemplate(compact),
                  gap: 16,
                  padding: "0 6px 10px",
                  borderBottom: `1px solid ${palette.line}`,
                  color: palette.textMuted,
                  fontSize: 12,
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                }}
              >
                <div>Event</div>
                <div>Classification</div>
                <div style={{ textAlign: "right" }}>Time</div>
              </div>
              {dayItems.map((item, index) => (
                <article
                  key={`${String(item.ts)}-${index}`}
                  style={{
                    background: "transparent",
                    borderTop: `1px solid ${palette.line}`,
                    padding: "18px 6px",
                  }}
                >
                  <div style={{ display: "grid", gridTemplateColumns: historyRowTemplate(compact), gap: 16, alignItems: "start" }}>
                    <div style={{ minWidth: 0 }}>
                      <strong style={{ display: "block", fontSize: 16 }}>{displayText(item.rule, "Unnamed rule")}</strong>
                      <div style={{ ...mutedStyle, lineHeight: 1.65, marginTop: 6 }}>
                        {displayText(item.reason, "No additional reason recorded for this event.")}
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                      <StatusPill text={displayText(item.action, "event")} tone="success" />
                      <StatusPill text={displayText(item.scope, "project")} />
                      {item.decision ? <StatusPill text={displayText(item.decision, "decision")} tone={decisionTone(displayText(item.decision, ""))} /> : null}
                    </div>
                    <div style={{ ...mutedStyle, fontSize: 13, whiteSpace: compact ? "normal" : "nowrap", textAlign: compact ? "left" : "right" }}>{displayText(item.ts, "-")}</div>
                  </div>
                </article>
              ))}
            </section>
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
  const focusHandlers = useFocusRing();
  const closeRef = useRef<HTMLButtonElement | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const titleId = `${title.toLowerCase().replace(/\s+/g, "-")}-title`;

  useEffect(() => {
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    closeRef.current?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Tab") return;
      const dialog = dialogRef.current;
      if (!dialog) return;
      const focusable = Array.from(
        dialog.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'),
      ).filter((element) => !element.hasAttribute("disabled") && element.tabIndex !== -1);
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (event.shiftKey) {
        if (!active || active === first) {
          event.preventDefault();
          last.focus();
        }
        return;
      }
      if (!active || active === last) {
        event.preventDefault();
        first.focus();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      previousFocus?.focus();
    };
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
      aria-labelledby={titleId}
      aria-describedby={`${titleId}-description`}
    >
      <div
        ref={dialogRef}
        onClick={(event) => event.stopPropagation()}
        style={{
          width: "min(860px, 100%)",
          maxHeight: "min(86vh, 920px)",
          overflow: "auto",
          background: "rgba(255,255,255,0.92)",
          border: `1px solid ${palette.line}`,
          borderRadius: 24,
          boxShadow: "0 18px 44px rgba(15, 23, 42, 0.10)",
          padding: 28,
        }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, marginBottom: 18 }}>
          <h2 id={titleId} style={{ ...sectionTitleStyle, marginBottom: 0 }}>{title}</h2>
          <button ref={closeRef} onClick={onClose} onFocus={focusHandlers.onFocus} onBlur={focusHandlers.onBlur} style={toneStyle("neutral")} aria-label={`Close ${title}`}>Close</button>
        </div>
        <p id={`${titleId}-description`} style={{ ...mutedStyle, marginTop: 0, marginBottom: 18, lineHeight: 1.6 }}>
          Review the primary summary first, then scan patterns, provenance, and actions.
        </p>
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
  const focusHandlers = useFocusRing();
  const summaryItems = [
    { label: "Learning scope", value: String(rule.learning_scope ?? "project") },
    { label: "Applies to", value: displayText(rule.scope, "unspecified") },
    { label: "Use count", value: String(rule.use_count ?? 0) },
    ...(rule.source_project ? [{ label: "Source project", value: String(rule.source_project) }] : []),
  ];
  const provenanceItems = [
    rule.decision_reason ? { label: "Decision reason", value: String(rule.decision_reason) } : null,
    rule.source_adapter ? { label: "Source adapter", value: String(rule.source_adapter) } : null,
    rule.source_event ? { label: "Source event", value: String(rule.source_event) } : null,
    rule.derived_from_candidate ? { label: "Derived from", value: String(rule.derived_from_candidate) } : null,
    rule.updated_at ? { label: "Updated at", value: String(rule.updated_at) } : null,
    rule.evidence_excerpt ? { label: "Evidence excerpt", value: String(rule.evidence_excerpt) } : null,
    rule.source ? { label: "Source", value: String(rule.source) } : null,
    rule.related_rule ? { label: "Related rule", value: String(rule.related_rule) } : null,
    rule.supersedes ? { label: "Supersedes", value: String(rule.supersedes) } : null,
  ].filter(Boolean) as Array<{ label: string; value: string }>;
  return (
    <div style={{ display: "grid", gap: 18 }}>
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "start" }}>
        <div>
          <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700, marginBottom: 8 }}>{RULE_DETAIL_MODAL_TITLE}</div>
          <strong style={{ fontSize: 22 }}>{String(rule.name)}</strong>
          <p style={{ ...mutedStyle, marginBottom: 0, lineHeight: 1.7 }}>{displayText(rule.summary, "No summary yet. This rule still needs curation.")}</p>
        </div>
        <StatusPill text={displayText(rule.status, "needs_review")} tone={String(rule.status) === "approved" ? "success" : "warning"} />
      </div>

      <Chips
        items={[
          `scope ${String(rule.learning_scope)}`,
          `applies ${displayText(rule.scope, "unspecified")}`,
          `uses ${String(rule.use_count)}`,
          rule.source_project ? `project ${String(rule.source_project)}` : "",
        ].filter(Boolean)}
      />

      <SectionBlock title="Primary details">
        <KeyValueGrid items={summaryItems} />
      </SectionBlock>

      <SectionBlock title="Why this exists">
        <p style={{ lineHeight: 1.75, margin: 0 }}>{displayText(rule.why, "No rationale has been written yet.")}</p>
      </SectionBlock>

      {String(rule.status) === "needs_review" ? (
        <SectionBlock title="Why this still needs review">
          <p style={{ lineHeight: 1.75, margin: 0, color: palette.amber }}>{unresolvedReasonText(rule.decision_reason || rule.why)}</p>
        </SectionBlock>
      ) : null}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 18 }}>
        <SectionBlock title="Good pattern">
          <p style={{ lineHeight: 1.75, margin: 0 }}>{displayText(rule.good_pattern, "No good-pattern guidance recorded.")}</p>
        </SectionBlock>
        <SectionBlock title="Avoid">
          <p style={{ lineHeight: 1.75, margin: 0 }}>{displayText(rule.avoid_pattern, "No avoid-pattern guidance recorded.")}</p>
        </SectionBlock>
      </div>

      <SectionBlock title="Provenance">
        {provenanceItems.length > 0 ? <KeyValueGrid items={provenanceItems} /> : <p style={{ ...mutedStyle, margin: 0 }}>No structured provenance has been recorded yet.</p>}
      </SectionBlock>

      {rule.learning_scope === "project" ? (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button onClick={() => onPromoteGlobal(String(rule.name))} onFocus={focusHandlers.onFocus} onBlur={focusHandlers.onBlur} style={{ ...toneStyle("primary"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>
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
  const focusHandlers = useFocusRing();
  const candidateItems = [
    { label: "Adapter", value: String(candidate.adapter ?? "-") },
    { label: "Decision", value: displayText(candidate.decision, "pending") },
    { label: "Confidence", value: String(candidate.confidence || "-") },
    ...(candidate.matched_rule ? [{ label: "Matched rule", value: String(candidate.matched_rule) }] : []),
  ];
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
      <SectionBlock title="Primary details">
        <KeyValueGrid items={candidateItems} />
      </SectionBlock>
      <SectionBlock title="Structured field diffs">
        {renderFieldDiffs(candidate.field_diffs)}
      </SectionBlock>
      <SectionBlock title="Why this stayed in review">
        <p style={{ lineHeight: 1.75, margin: 0, color: palette.amber }}>{unresolvedReasonText(candidate.decision_reason)}</p>
      </SectionBlock>
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <button onClick={() => onReviewCandidate(String(candidate.path), "approve")} onFocus={focusHandlers.onFocus} onBlur={focusHandlers.onBlur} style={{ ...toneStyle("primary"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>Approve</button>
        <button onClick={() => onReviewCandidate(String(candidate.path), "needs-review")} onFocus={focusHandlers.onFocus} onBlur={focusHandlers.onBlur} style={{ ...toneStyle("neutral"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>Needs Review</button>
        <button onClick={() => onReviewCandidate(String(candidate.path), "reject")} onFocus={focusHandlers.onFocus} onBlur={focusHandlers.onBlur} style={{ ...toneStyle("danger"), opacity: disabled ? 0.6 : 1 }} disabled={disabled}>Reject</button>
      </div>
    </div>
  );
}
