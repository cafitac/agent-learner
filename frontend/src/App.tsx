import React, { useEffect, useMemo, useState } from "react";
import { CandidateModalContent, CandidatesPanel, CountList, DetailModal, HistoryTable, ProjectSelector, RuleModalContent, RulesPanel, StatStrip } from "./components";
import { Summary, cardStyle, pageStyle, panelStyle, palette } from "./types";

function textValue(value: unknown) {
  return String(value ?? "").trim();
}

function isLowSignalDraft(rule: Record<string, unknown>) {
  const status = textValue(rule.status);
  const summary = textValue(rule.summary);
  const scopeText = textValue(rule.scope);
  return status === "draft" && !summary && !scopeText;
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

  async function load(projectOverride?: string) {
    const effectiveProject = projectOverride ?? selectedProject;
    const suffix = effectiveProject ? `?project=${encodeURIComponent(effectiveProject)}` : "";
    const res = await fetch(`/api/summary${suffix}`);
    if (!res.ok) throw new Error(await res.text());
    const json = (await res.json()) as Summary;
    setSummary(json);
    setSelectedProject(json.project.root);
    const curatedRules = ((json.merged.rules as Record<string, unknown>[]) ?? []).filter((rule) => !isLowSignalDraft(rule));
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
    const curated = ((summary.merged.rules as Record<string, unknown>[]) ?? []).filter((rule) => !isLowSignalDraft(rule));
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

  return (
    <div style={{ ...pageStyle, scrollBehavior: "smooth" }}>
      <div style={{ maxWidth: 1360, margin: "0 auto", padding: "40px 24px 72px" }}>
        <section style={{ ...panelStyle, borderRadius: 36, padding: 32, boxShadow: palette.shadow }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20, alignItems: "start" }}>
            <div>
              <div style={{ display: "inline-flex", alignItems: "center", padding: "8px 12px", borderRadius: 999, background: "rgba(255,255,255,0.72)", border: `1px solid ${palette.line}`, color: palette.textMuted, fontSize: 13, fontWeight: 600 }}>
                agent learning control plane
              </div>
              <h1 style={{ marginTop: 16, marginBottom: 10, fontSize: "clamp(30px, 4.5vw, 42px)", lineHeight: 1.06, letterSpacing: "-0.05em" }}>Reusable learning, organized by task.</h1>
              <p style={{ color: palette.textMuted, marginTop: 0, marginBottom: 0, fontSize: 16, lineHeight: 1.6, maxWidth: 640 }}>
                Use overview for status, rules for reusable guidance, candidates for triage, and history for audit.
              </p>
            </div>
            <div style={{ ...panelStyle, padding: 18, borderRadius: 24, background: "rgba(255,255,255,0.7)" }}>
              <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>Runtime Status</div>
              <p style={{ color: statusTone === "error" ? palette.red : statusTone === "success" ? palette.green : palette.textMuted, marginTop: 8, marginBottom: 0, lineHeight: 1.55, fontSize: 14 }}>
                {status}
              </p>
            </div>
          </div>
          <div style={{ height: 1, background: palette.line, margin: "24px 0" }} />
          <nav style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 18 }}>
            {navItems.map(({ key, label }) => (
              <a
                key={key}
                href={key === "overview" ? "#" : `#${key}`}
                onClick={() => setPage(key)}
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
          <p style={{ color: statusTone === "error" ? palette.red : statusTone === "success" ? palette.green : palette.textMuted, marginTop: 0 }}>
            {status}
          </p>
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
                    { label: "Curated", value: ((summary.merged.rules as Record<string, unknown>[]) ?? []).filter((rule) => !isLowSignalDraft(rule)).length },
                    { label: "Candidates", value: summary.overview.candidates },
                    { label: "History", value: summary.overview.global_history_entries },
                  ]}
                />
              </div>
              <div style={{ marginTop: 24, display: "grid", gap: 12 }}>
                <article style={cardStyle}>
                  <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>Recommended next area</div>
                  <h3 style={{ marginBottom: 8, fontSize: 22, letterSpacing: "-0.03em" }}>Start with curated rules</h3>
                  <p style={{ marginTop: 0, color: palette.textMuted, lineHeight: 1.65 }}>
                    Curated rules are the fastest way to understand what this project has already learned and what guidance is most reusable.
                  </p>
                  <a
                    href="#rules"
                    onClick={() => setPage("rules")}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      marginTop: 8,
                      padding: "10px 14px",
                      borderRadius: 999,
                      background: palette.blue,
                      color: "white",
                      textDecoration: "none",
                      fontWeight: 600,
                    }}
                  >
                    Open Rules
                  </a>
                </article>
                <article style={{ ...cardStyle, display: "grid", gap: 10 }}>
                  <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>At a glance</div>
                  <div style={{ color: palette.textMuted, lineHeight: 1.65 }}>
                    {summary.overview.candidates > 0
                      ? `${summary.overview.candidates} candidate items are waiting for review.`
                      : "There are no pending candidates right now."}
                  </div>
                  <div style={{ color: palette.textMuted, lineHeight: 1.65 }}>
                    {summary.overview.global_history_entries > 0
                      ? `${summary.overview.global_history_entries} global history event(s) are available for audit.`
                      : "No global history has been recorded yet."}
                  </div>
                </article>
              </div>
            </>
          ) : null}
        </section>

        {page === "rules" ? (
          <div id="rules" style={{ marginTop: 24 }}>
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
            />
          </div>
        ) : null}

        {page === "candidates" ? (
          <div id="candidates" style={{ marginTop: 24 }}>
            <CandidatesPanel
              candidates={summary?.candidates ?? []}
              onReviewCandidate={reviewCandidate}
              onSelectCandidate={(path) => {
                setSelectedCandidatePath(path);
                setActiveModal({ type: "candidate", key: path });
              }}
              disabled={actionPending}
            />
          </div>
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
            <div id="history" style={{ marginTop: 24 }}>
              <HistoryTable items={summary?.recent_history ?? []} filter={historyFilter} setFilter={setHistoryFilter} />
            </div>
          </>
        ) : null}
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
