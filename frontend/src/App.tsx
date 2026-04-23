import React, { useEffect, useMemo, useState } from "react";
import { CandidateModalContent, CandidatesPanel, CountList, DetailModal, HistoryTable, ProjectSelector, RuleModalContent, RulesPanel, StatStrip } from "./components";
import { Summary, focusRingStyle, pageStyle, panelStyle, palette } from "./types";

function textValue(value: unknown) {
  return String(value ?? "").trim();
}

function isLowSignalDraft(rule: Record<string, unknown>) {
  const status = textValue(rule.status);
  const summary = textValue(rule.summary);
  const scopeText = textValue(rule.scope);
  return status === "draft" && !summary && !scopeText;
}

function isPlaceholderRuleName(name: unknown) {
  const value = textValue(name);
  return value.startsWith("learned-rule-draft-") || value.startsWith("session-learning-");
}

function isCuratedRule(rule: Record<string, unknown>) {
  const status = textValue(rule.status);
  const summary = textValue(rule.summary);
  const scopeText = textValue(rule.scope);
  const why = textValue(rule.why);
  return status === "approved" && !!summary && !!scopeText && !!why && !isPlaceholderRuleName(rule.name);
}

function applyFocusRing(event: React.FocusEvent<HTMLElement>) {
  Object.assign(event.currentTarget.style, {
    outline: String(focusRingStyle.outline),
    outlineOffset: `${focusRingStyle.outlineOffset ?? 2}px`,
    boxShadow: String(focusRingStyle.boxShadow),
  });
}

function clearFocusRing(event: React.FocusEvent<HTMLElement>) {
  event.currentTarget.style.outline = "";
  event.currentTarget.style.outlineOffset = "";
  event.currentTarget.style.boxShadow = "";
}

export function App() {
  const getInitialPage = () => {
    const hash = window.location.hash.replace("#", "");
    if (hash === "rules" || hash === "candidates" || hash === "history") return hash as "rules" | "candidates" | "history";
    return "overview" as const;
  };
  const [summary, setSummary] = useState<Summary | null>(null);
  const [scope, setScope] = useState<"curated" | "drafts" | "local" | "global">("curated");
  const [page, setPage] = useState<"overview" | "rules" | "candidates" | "history">(getInitialPage);
  const [status, setStatus] = useState("Loading...");
  const [statusTone, setStatusTone] = useState<"neutral" | "success" | "error">("neutral");
  const [actionPending, setActionPending] = useState(false);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [promoteAllProjects, setPromoteAllProjects] = useState(false);
  const [selectedRuleName, setSelectedRuleName] = useState<string>("");
  const [selectedCandidatePath, setSelectedCandidatePath] = useState<string>("");
  const [historyFilter, setHistoryFilter] = useState<string>("");
  const [ruleFilter, setRuleFilter] = useState<string>("");
  const [activeModal, setActiveModal] = useState<null | { type: "rule"; key: string } | { type: "candidate"; key: string }>(null);
  const [isCompactLayout, setIsCompactLayout] = useState(false);

  async function load(projectOverride?: string) {
    const effectiveProject = projectOverride ?? selectedProject;
    const suffix = effectiveProject ? `?project=${encodeURIComponent(effectiveProject)}` : "";
    const res = await fetch(`/api/summary${suffix}`);
    if (!res.ok) throw new Error(await res.text());
    const json = (await res.json()) as Summary;
    setSummary(json);
    setSelectedProject(json.project.root);
    const curatedRules = ((json.merged.rules as Record<string, unknown>[]) ?? []).filter((rule) => isCuratedRule(rule));
    setSelectedRuleName((prev) => {
      const available = new Set(curatedRules.map((rule) => String(rule.name)));
      if (prev && available.has(prev)) return prev;
      return String(curatedRules[0]?.name ?? json.local.rules[0]?.name ?? json.global.rules[0]?.name ?? "");
    });
    setSelectedCandidatePath((prev) => {
      const available = new Set((json.candidates ?? []).map((candidate) => String(candidate.path)));
      if (prev && available.has(prev)) return prev;
      return String(json.candidates[0]?.path ?? "");
    });
    setStatus(`Loaded. Latest activity: ${json.overview.latest_activity || "-"}`);
    setStatusTone("neutral");
  }

  useEffect(() => {
    load().catch((err) => {
      setStatus(String(err));
      setStatusTone("error");
    });
  }, []);

  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash.replace("#", "");
      if (hash === "rules" || hash === "candidates" || hash === "history") setPage(hash);
      else setPage("overview");
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  useEffect(() => {
    if (!selectedProject) return;
    load(selectedProject).catch((err) => {
      setStatus(String(err));
      setStatusTone("error");
    });
  }, [selectedProject]);

  useEffect(() => {
    if (!activeModal) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setActiveModal(null);
    };
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", onKeyDown);
    };
  }, [activeModal]);

  useEffect(() => {
    const query = window.matchMedia("(max-width: 920px)");
    const applyLayout = () => setIsCompactLayout(query.matches);
    applyLayout();
    query.addEventListener("change", applyLayout);
    return () => query.removeEventListener("change", applyLayout);
  }, []);

  async function promoteGlobal(name: string) {
    try {
      setActionPending(true);
      setStatus(`Promoting ${name}...`);
      setStatusTone("neutral");
      const res = await fetch("/api/promote-global", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, all_projects: promoteAllProjects, project: selectedProject || summary?.project.root }),
      });
      if (!res.ok) throw new Error(await res.text());
      await load(selectedProject || summary?.project.root);
      setStatus(`Promoted ${name} to global learning.`);
      setStatusTone("success");
    } catch (err) {
      setStatus(String(err));
      setStatusTone("error");
    } finally {
      setActionPending(false);
    }
  }

  async function reviewCandidate(candidate: string, action: "approve" | "reject" | "needs-review") {
    try {
      setActionPending(true);
      setStatus(`Applying ${action} to candidate...`);
      setStatusTone("neutral");
      const res = await fetch("/api/review-candidate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ candidate, action, project: selectedProject || summary?.project.root }),
      });
      if (!res.ok) throw new Error(await res.text());
      await load(selectedProject || summary?.project.root);
      setStatus(`Candidate action complete: ${action}.`);
      setStatusTone("success");
    } catch (err) {
      setStatus(String(err));
      setStatusTone("error");
    } finally {
      setActionPending(false);
    }
  }

  const ruleCollections = useMemo(() => {
    if (!summary) return null;
    const curated = ((summary.merged.rules as Record<string, unknown>[]) ?? []).filter((rule) => isCuratedRule(rule));
    const local = (summary.local.rules as Record<string, unknown>[]) ?? [];
    const global = (summary.global.rules as Record<string, unknown>[]) ?? [];
    const drafts = [...local, ...global].filter((rule) => {
      const status = textValue(rule.status);
      return status === "draft" || status === "needs_review";
    });
    return { curated, drafts, local, global };
  }, [summary]);
  const rules = useMemo(() => (ruleCollections ? ruleCollections[scope] : []), [ruleCollections, scope]);
  const filteredRules = useMemo(() => {
    const normalizedFilter = ruleFilter.toLowerCase().trim();
    if (!normalizedFilter) return rules;
    return rules.filter((rule) =>
      [
        rule.name,
        rule.summary,
        rule.scope,
        rule.why,
        rule.good_pattern,
        rule.avoid_pattern,
        rule.source_project,
      ]
        .map((value) => String(value ?? "").toLowerCase())
        .join(" ")
        .includes(normalizedFilter),
    );
  }, [rules, ruleFilter]);
  const ruleCounts = useMemo(
    () =>
      ruleCollections
        ? {
            curated: ruleCollections.curated.length,
            drafts: ruleCollections.drafts.length,
            local: ruleCollections.local.length,
            global: ruleCollections.global.length,
          }
        : { curated: 0, drafts: 0, local: 0, global: 0 },
    [ruleCollections],
  );
  const selectedRule = useMemo(
    () => ((ruleCollections ? [...ruleCollections.curated, ...ruleCollections.drafts, ...ruleCollections.local, ...ruleCollections.global] : []).find((rule) => String(rule.name) === selectedRuleName) as Record<string, unknown> | undefined) ?? null,
    [ruleCollections, selectedRuleName],
  );
  const selectedCandidate = useMemo(
    () => (summary?.candidates.find((candidate) => String(candidate.path) === selectedCandidatePath) as Record<string, unknown> | undefined) ?? null,
    [summary, selectedCandidatePath],
  );

  const navItems: Array<{ key: "overview" | "rules" | "candidates" | "history"; label: string }> = [
    { key: "overview", label: "Overview" },
    { key: "rules", label: "Rules" },
    { key: "candidates", label: "Candidates" },
    { key: "history", label: "History" },
  ];
  const curatedCount = ((summary?.merged.rules as Record<string, unknown>[]) ?? []).filter((rule) => isCuratedRule(rule)).length;
  const nextStep = useMemo(() => {
    if (!summary) {
      return {
        eyebrow: "Recommended next step",
        title: "Load dashboard data",
        description: "Once the project summary loads, the dashboard can point you to the highest-value next action.",
        ctaLabel: "Stay on overview",
        ctaPage: "overview" as const,
      };
    }
    if (summary.overview.candidates > 0) {
      return {
        eyebrow: "Recommended next step",
        title: "Review pending candidates first",
        description: `${summary.overview.candidates} candidate item(s) are waiting for a decision before they become trusted reusable guidance.`,
        ctaLabel: "Review candidates",
        ctaPage: "candidates" as const,
      };
    }
    if (curatedCount === 0) {
      return {
        eyebrow: "Recommended next step",
        title: "Curate your first reusable rule",
        description: "There is no curated rule yet, so start in Rules and promote the highest-signal guidance into the stable set.",
        ctaLabel: "Open rules",
        ctaPage: "rules" as const,
      };
    }
    if (summary.overview.global_history_entries > 0) {
      return {
        eyebrow: "Recommended next step",
        title: "Audit recent learning changes",
        description: `${summary.overview.global_history_entries} global history event(s) are available if you want to confirm what changed and why.`,
        ctaLabel: "Open history",
        ctaPage: "history" as const,
      };
    }
    return {
      eyebrow: "Recommended next step",
      title: "Browse curated rules",
      description: "Curated rules are the fastest way to understand what this project has already learned and what guidance is most reusable.",
      ctaLabel: "Open rules",
      ctaPage: "rules" as const,
    };
  }, [curatedCount, summary]);
  const overviewQueue = useMemo(() => {
    if (!summary) return [];
    const items: Array<{
      key: string;
      priority: "Now" | "Soon" | "Later";
      title: string;
      description: string;
      ctaLabel: string;
      ctaPage: "overview" | "rules" | "candidates" | "history";
      tone: "neutral" | "success" | "warning";
    }> = [];

    items.push({
      key: "candidates",
      priority: summary.overview.candidates > 0 ? "Now" : "Later",
      title: summary.overview.candidates > 0 ? "Review pending candidates" : "Candidate queue is clear",
      description:
        summary.overview.candidates > 0
          ? `${summary.overview.candidates} item(s) still need review before they become trusted reusable guidance.`
          : "No candidate items are waiting for review right now.",
      ctaLabel: "Open candidates",
      ctaPage: "candidates",
      tone: summary.overview.candidates > 0 ? "warning" : "success",
    });

    items.push({
      key: "rules",
      priority: curatedCount === 0 || ruleCounts.drafts > 0 ? "Soon" : "Later",
      title: curatedCount === 0 ? "Curate your first stable rule" : "Keep rules tidy",
      description:
        curatedCount === 0
          ? "There is no curated rule yet, so promote the highest-signal guidance into the stable set."
          : ruleCounts.drafts > 0
            ? `${ruleCounts.drafts} draft rule(s) still need curation before they are reliable.`
            : `${curatedCount} curated rule(s) are available for reuse.`,
      ctaLabel: "Open rules",
      ctaPage: "rules",
      tone: curatedCount === 0 || ruleCounts.drafts > 0 ? "warning" : "success",
    });

    items.push({
      key: "history",
      priority: summary.overview.global_history_entries > 0 ? "Soon" : "Later",
      title: summary.overview.global_history_entries > 0 ? "Audit recent changes" : "Audit trail will appear here",
      description:
        summary.overview.global_history_entries > 0
          ? `${summary.overview.global_history_entries} global history event(s) are ready for audit and provenance review.`
          : "Once reviews and promotions happen, history becomes your lightweight provenance timeline.",
      ctaLabel: "Open history",
      ctaPage: "history",
      tone: "neutral",
    });

    const order = { Now: 0, Soon: 1, Later: 2 };
    return items.sort((a, b) => order[a.priority] - order[b.priority]);
  }, [curatedCount, ruleCounts.drafts, summary]);
  const onboardingSteps = [
    {
      title: "1. Capture",
      description: "Learning events and candidates accumulate from real work instead of requiring manual setup first.",
    },
    {
      title: "2. Review",
      description: "Candidates stay reviewable until you approve, reject, or keep them in needs-review state.",
    },
    {
      title: "3. Reuse",
      description: "Curated rules become the reusable, high-signal guidance layer across projects.",
    },
  ];
  const overviewHealth = useMemo(() => {
    if (!summary) return [];
    return [
      {
        key: "review-load",
        label: "Review Load",
        value: summary.overview.candidates > 0 ? `${summary.overview.candidates} pending` : "Clear",
        tone: summary.overview.candidates > 0 ? ("warning" as const) : ("success" as const),
        description:
          summary.overview.candidates > 0
            ? "Candidate review is the highest-priority queue right now."
            : "No candidate backlog is waiting for operator review.",
      },
      {
        key: "rule-health",
        label: "Rule Health",
        value: curatedCount === 0 ? "Needs curation" : ruleCounts.drafts > 0 ? `${curatedCount} stable / ${ruleCounts.drafts} draft` : `${curatedCount} stable`,
        tone: curatedCount === 0 || ruleCounts.drafts > 0 ? ("warning" as const) : ("success" as const),
        description:
          curatedCount === 0
            ? "Reusable guidance is not stabilized yet."
            : ruleCounts.drafts > 0
              ? "Stable rules exist, but drafts still need curation."
              : "Reusable guidance is in a healthy curated state.",
      },
      {
        key: "audit-coverage",
        label: "Audit Coverage",
        value: summary.overview.global_history_entries > 0 ? `${summary.overview.global_history_entries} events` : "No history yet",
        tone: summary.overview.global_history_entries > 0 ? ("neutral" as const) : ("warning" as const),
        description:
          summary.overview.global_history_entries > 0
            ? "Recent changes are traceable through the audit timeline."
            : "Audit visibility will improve once review and promotion events accumulate.",
      },
    ];
  }, [curatedCount, ruleCounts.drafts, summary]);
  const isQuietWorkspace =
    !!summary &&
    summary.overview.candidates === 0 &&
    summary.overview.global_history_entries === 0 &&
    curatedCount === 0;

  return (
    <div style={{ ...pageStyle, scrollBehavior: "smooth" }}>
      <a
        href="#main-content"
        onFocus={(event) => {
          applyFocusRing(event);
          event.currentTarget.style.transform = "translateY(0)";
        }}
        onBlur={(event) => {
          clearFocusRing(event);
          event.currentTarget.style.transform = "translateY(-140%)";
        }}
        style={{
          position: "absolute",
          left: 24,
          top: 12,
          padding: "10px 14px",
          borderRadius: 12,
          background: palette.text,
          color: "white",
          textDecoration: "none",
          fontWeight: 600,
          transform: "translateY(-140%)",
          transition: "transform 160ms ease",
          zIndex: 10,
        }}
      >
        Skip to main content
      </a>
      <div style={{ maxWidth: 1360, margin: "0 auto", padding: "40px 24px 72px" }}>
        <header style={{ ...panelStyle, borderRadius: 36, padding: 32, boxShadow: palette.shadow }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20, alignItems: "start" }}>
            <div>
              <div style={{ display: "inline-flex", alignItems: "center", padding: "8px 12px", borderRadius: 999, background: "rgba(255,255,255,0.72)", border: `1px solid ${palette.line}`, color: palette.textMuted, fontSize: 13, fontWeight: 600 }}>
                agent learning control plane
              </div>
              <h1 style={{ marginTop: 16, marginBottom: 10, fontSize: "clamp(30px, 4.5vw, 42px)", lineHeight: 1.06, letterSpacing: "-0.05em" }}>Reusable learning, organized for review.</h1>
              <p style={{ color: palette.textMuted, marginTop: 0, marginBottom: 0, fontSize: 16, lineHeight: 1.6, maxWidth: 640 }}>
                Use Overview for queue health, Rules for reusable guidance, Candidates for review, and History for audit.
              </p>
            </div>
            <div style={{ ...panelStyle, padding: 18, borderRadius: 24, background: "rgba(255,255,255,0.7)" }}>
              <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>Runtime Status</div>
              <p aria-live="polite" role="status" style={{ color: statusTone === "error" ? palette.red : statusTone === "success" ? palette.green : palette.textMuted, marginTop: 8, marginBottom: 0, lineHeight: 1.55, fontSize: 14 }}>
                {status}
              </p>
            </div>
          </div>
          <div style={{ height: 1, background: palette.line, margin: "24px 0" }} />
          <nav aria-label="Dashboard sections" style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 18 }}>
            {navItems.map(({ key, label }) => (
              <a
                key={key}
                href={key === "overview" ? "#" : `#${key}`}
                onClick={() => setPage(key)}
                onFocus={applyFocusRing}
                onBlur={clearFocusRing}
                aria-current={page === key ? "page" : undefined}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  padding: "10px 14px",
                  borderRadius: 999,
                  border: `1px solid ${page === key ? palette.text : palette.line}`,
                  background: page === key ? palette.text : "rgba(255,255,255,0.74)",
                  color: page === key ? "white" : palette.text,
                  textDecoration: "none",
                  fontWeight: 600,
                  fontSize: 14,
                  backdropFilter: "blur(10px)",
                }}
              >
                {label}
              </a>
            ))}
          </nav>
        </header>
        <main id="main-content" tabIndex={-1} style={{ outline: "none" }}>
          {summary && page === "overview" ? (
            <>
              <ProjectSelector
                summary={summary}
                selectedProject={selectedProject}
                setSelectedProject={setSelectedProject}
                promoteAllProjects={promoteAllProjects}
                setPromoteAllProjects={setPromoteAllProjects}
              />
              <div id="overview" style={{ marginTop: 22 }}>
                <StatStrip
                  items={[
                    { label: "Local Rules", value: summary.overview.local_rules },
                    { label: "Curated Rules", value: curatedCount },
                    { label: "Pending Candidates", value: summary.overview.candidates },
                    { label: "Global History", value: summary.overview.global_history_entries },
                  ]}
                />
              </div>
              {isQuietWorkspace ? (
                <section style={{ ...panelStyle, marginTop: 18, padding: 20, borderRadius: 20, background: "rgba(255,255,255,0.78)" }}>
                  <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>Quiet workspace</div>
                  <h3 style={{ marginTop: 10, marginBottom: 8, fontSize: 22, letterSpacing: "-0.03em" }}>Nothing urgent is waiting yet</h3>
                  <p style={{ margin: 0, color: palette.textMuted, lineHeight: 1.65 }}>
                    This workspace does not have pending candidates, curated rules, or audit history yet. That usually means capture and review have not started, not that the dashboard is broken.
                  </p>
                </section>
              ) : null}
              <div style={{ marginTop: 24, display: "grid", gap: 12 }}>
                <section style={{ display: "grid", gap: 14, paddingTop: 18, borderTop: `1px solid ${palette.line}` }}>
                  <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>{nextStep.eyebrow}</div>
                  <div style={{ display: "grid", gridTemplateColumns: "minmax(0, 1.2fr) auto", gap: 16, alignItems: "center" }}>
                    <div>
                      <h3 style={{ margin: 0, fontSize: 22, letterSpacing: "-0.03em" }}>{nextStep.title}</h3>
                      <p style={{ marginTop: 8, marginBottom: 0, color: palette.textMuted, lineHeight: 1.65 }}>
                        {nextStep.description}
                      </p>
                    </div>
                    <a
                      href={nextStep.ctaPage === "overview" ? "#" : `#${nextStep.ctaPage}`}
                      onClick={() => setPage(nextStep.ctaPage)}
                      onFocus={applyFocusRing}
                      onBlur={clearFocusRing}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        padding: "10px 14px",
                        borderRadius: 999,
                        background: palette.blue,
                        color: "white",
                        textDecoration: "none",
                        fontWeight: 600,
                        whiteSpace: "nowrap",
                      }}
                    >
                      {nextStep.ctaLabel}
                    </a>
                  </div>
                </section>
                <section style={{ display: "grid", gap: 12, paddingTop: 18, borderTop: `1px solid ${palette.line}` }}>
                  <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>Health summary</div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
                    {overviewHealth.map((item) => (
                      <article key={item.key} style={{ ...panelStyle, padding: 18, borderRadius: 18, background: "rgba(255,255,255,0.76)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center" }}>
                          <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>{item.label}</div>
                          <span
                            aria-label={`${item.label}: ${item.value}`}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              padding: "6px 10px",
                              borderRadius: 999,
                              background:
                                item.tone === "success" ? palette.greenSoft : item.tone === "warning" ? palette.amberSoft : "rgba(17,17,17,0.04)",
                              color: item.tone === "success" ? palette.green : item.tone === "warning" ? palette.amber : palette.textMuted,
                              border: `1px solid ${item.tone === "success" ? palette.greenSoft : item.tone === "warning" ? palette.amberSoft : palette.line}`,
                              fontSize: 12,
                              fontWeight: 700,
                            }}
                          >
                            {item.value}
                          </span>
                        </div>
                        <p style={{ marginTop: 12, marginBottom: 0, color: palette.textMuted, lineHeight: 1.6 }}>{item.description}</p>
                      </article>
                    ))}
                  </div>
                </section>
                <section style={{ display: "grid", gap: 12, paddingTop: 18, borderTop: `1px solid ${palette.line}` }}>
                  <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>Action queue</div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 12 }}>
                    {overviewQueue.map((item) => (
                      <article key={item.key} style={{ ...panelStyle, padding: 18, borderRadius: 18, background: "rgba(255,255,255,0.76)" }}>
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "start" }}>
                          <div>
                            <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>{item.priority}</div>
                            <strong style={{ display: "block", marginTop: 8, fontSize: 17 }}>{item.title}</strong>
                          </div>
                          <span
                            aria-label={`Priority ${item.priority}`}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              padding: "6px 10px",
                              borderRadius: 999,
                              background:
                                item.tone === "success" ? palette.greenSoft : item.tone === "warning" ? palette.amberSoft : "rgba(17,17,17,0.04)",
                              color: item.tone === "success" ? palette.green : item.tone === "warning" ? palette.amber : palette.textMuted,
                              border: `1px solid ${item.tone === "success" ? palette.greenSoft : item.tone === "warning" ? palette.amberSoft : palette.line}`,
                              fontSize: 12,
                              fontWeight: 700,
                            }}
                          >
                            {item.priority}
                          </span>
                        </div>
                        <p style={{ marginTop: 10, marginBottom: 16, color: palette.textMuted, lineHeight: 1.6 }}>{item.description}</p>
                        <a
                          href={item.ctaPage === "overview" ? "#" : `#${item.ctaPage}`}
                          onClick={() => setPage(item.ctaPage)}
                          onFocus={applyFocusRing}
                          onBlur={clearFocusRing}
                          style={{
                            display: "inline-flex",
                            alignItems: "center",
                            padding: "10px 14px",
                            borderRadius: 999,
                            background: palette.text,
                            color: "white",
                            textDecoration: "none",
                            fontWeight: 600,
                          }}
                        >
                          {item.ctaLabel}
                        </a>
                      </article>
                    ))}
                  </div>
                </section>
                <section style={{ display: "grid", gap: 12, paddingTop: 18, borderTop: `1px solid ${palette.line}` }}>
                  <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>How this dashboard works</div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
                    {onboardingSteps.map((step) => (
                      <article key={step.title} style={{ ...panelStyle, padding: 18, borderRadius: 18, background: "rgba(255,255,255,0.72)" }}>
                        <strong style={{ display: "block", fontSize: 15 }}>{step.title}</strong>
                        <p style={{ marginTop: 8, marginBottom: 0, color: palette.textMuted, lineHeight: 1.6 }}>{step.description}</p>
                      </article>
                    ))}
                  </div>
                </section>
                <section style={{ display: "grid", gap: 10, paddingTop: 18, borderTop: `1px solid ${palette.line}` }}>
                  <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>Operator notes</div>
                  <div style={{ color: palette.textMuted, lineHeight: 1.65 }}>
                    {summary.overview.candidates > 0
                      ? `${summary.overview.candidates} candidate item(s) are waiting for review.`
                      : "There are no pending candidates right now."}
                  </div>
                  <div style={{ color: palette.textMuted, lineHeight: 1.65 }}>
                    {summary.overview.global_history_entries > 0
                      ? `${summary.overview.global_history_entries} global history event(s) are available for audit.`
                      : "No global history has been recorded yet."}
                  </div>
                  <div style={{ color: palette.textMuted, lineHeight: 1.65 }}>
                    Candidate queues are ordered by review urgency first. Rules surfaces prioritize curated guidance and unfinished review work before lower-signal leftovers.
                  </div>
                  <div style={{ color: palette.textMuted, lineHeight: 1.65 }}>
                    Dashboard is for viewing and managing learned guidance. Capture and activation still happen through your adapter install/bootstrap flow.
                  </div>
                  {isQuietWorkspace ? (
                    <div style={{ color: palette.textMuted, lineHeight: 1.65 }}>
                      If this is a fresh setup, start by running real work through the adapter flow, then return here to review the first candidate or curate the first stable rule.
                    </div>
                  ) : null}
                </section>
              </div>
            </>
          ) : null}

        {page === "rules" ? (
          <section id="rules" aria-label="Rules" style={{ marginTop: 24 }}>
            <RulesPanel
              scope={scope}
              setScope={setScope}
              rules={filteredRules}
              counts={ruleCounts}
              ruleFilter={ruleFilter}
              setRuleFilter={setRuleFilter}
              onPromoteGlobal={promoteGlobal}
              onSelectRule={(name) => {
                setSelectedRuleName(name);
                setActiveModal({ type: "rule", key: name });
              }}
              disabled={actionPending}
              compact={isCompactLayout}
            />
          </section>
        ) : null}

        {page === "candidates" ? (
          <section id="candidates" aria-label="Candidates" style={{ marginTop: 24 }}>
            <CandidatesPanel
              candidates={summary?.candidates ?? []}
              onReviewCandidate={reviewCandidate}
              onSelectCandidate={(path) => {
                setSelectedCandidatePath(path);
                setActiveModal({ type: "candidate", key: path });
              }}
              disabled={actionPending}
              compact={isCompactLayout}
            />
          </section>
        ) : null}

        {page === "history" ? (
          <>
            {summary ? (
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 18, marginTop: 24 }}>
                <CountList title="History by Action" data={summary.history_summary.by_action} />
                <CountList title="History by Adapter" data={summary.history_summary.by_adapter} />
                <CountList title="History by Decision" data={summary.history_summary.by_decision} />
              </div>
            ) : null}
            <section id="history" aria-label="History" style={{ marginTop: 24 }}>
              <HistoryTable items={summary?.recent_history ?? []} filter={historyFilter} setFilter={setHistoryFilter} compact={isCompactLayout} />
            </section>
          </>
        ) : null}
        </main>
      </div>

      {activeModal?.type === "rule" && selectedRule ? (
        <DetailModal title="Rule Detail" onClose={() => setActiveModal(null)}>
          <RuleModalContent rule={selectedRule} onPromoteGlobal={promoteGlobal} disabled={actionPending} />
        </DetailModal>
      ) : null}

      {activeModal?.type === "candidate" && selectedCandidate ? (
        <DetailModal title="Candidate Detail" onClose={() => setActiveModal(null)}>
          <CandidateModalContent candidate={selectedCandidate} onReviewCandidate={reviewCandidate} disabled={actionPending} />
        </DetailModal>
      ) : null}
    </div>
  );
}
