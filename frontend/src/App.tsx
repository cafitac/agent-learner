import React, { useEffect, useMemo, useState } from "react";
import { CandidateDetailPanel, CandidatesPanel, CountList, HistoryTable, MetricCard, ProjectSelector, RuleDetailPanel, RulesPanel } from "./components";
import { Summary, pageStyle, panelStyle, palette } from "./types";

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
  const [summary, setSummary] = useState<Summary | null>(null);
  const [scope, setScope] = useState<"curated" | "drafts" | "local" | "global">("curated");
  const [status, setStatus] = useState("Loading...");
  const [statusTone, setStatusTone] = useState<"neutral" | "success" | "error">("neutral");
  const [actionPending, setActionPending] = useState(false);
  const [selectedProject, setSelectedProject] = useState<string>("");
  const [promoteAllProjects, setPromoteAllProjects] = useState(false);
  const [selectedRuleName, setSelectedRuleName] = useState<string>("");
  const [selectedCandidatePath, setSelectedCandidatePath] = useState<string>("");
  const [historyFilter, setHistoryFilter] = useState<string>("");

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
    if (!selectedProject) return;
    load(selectedProject).catch((err) => {
      setStatus(String(err));
      setStatusTone("error");
    });
  }, [selectedProject]);

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
    () => (rules.find((rule) => String(rule.name) === selectedRuleName) as Record<string, unknown> | undefined) ?? null,
    [rules, selectedRuleName],
  );
  const selectedCandidate = useMemo(
    () => (summary?.candidates.find((candidate) => String(candidate.path) === selectedCandidatePath) as Record<string, unknown> | undefined) ?? null,
    [summary, selectedCandidatePath],
  );

  return (
    <div style={pageStyle}>
      <div style={{ maxWidth: 1360, margin: "0 auto", padding: "40px 24px 72px" }}>
        <section style={{ ...panelStyle, borderRadius: 36, padding: 32, boxShadow: palette.shadow }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 24, alignItems: "end" }}>
            <div>
              <div style={{ display: "inline-flex", alignItems: "center", padding: "8px 12px", borderRadius: 999, background: "rgba(255,255,255,0.72)", border: `1px solid ${palette.line}`, color: palette.textMuted, fontSize: 13, fontWeight: 600 }}>
                agent learning control plane
              </div>
              <h1 style={{ marginTop: 18, marginBottom: 12, fontSize: "clamp(36px, 6vw, 56px)", lineHeight: 1.02, letterSpacing: "-0.06em" }}>A cleaner view of reusable learning.</h1>
              <p style={{ color: palette.textMuted, marginTop: 0, marginBottom: 0, fontSize: 18, lineHeight: 1.6, maxWidth: 720 }}>
                Review project-local rules, global learning assets, candidates, and promotion history from one calm dashboard.
              </p>
            </div>
            <div style={{ ...panelStyle, padding: 20, borderRadius: 24, background: "rgba(255,255,255,0.7)" }}>
              <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: "0.08em", color: palette.textMuted, fontWeight: 700 }}>Runtime Status</div>
              <p style={{ color: statusTone === "error" ? palette.red : statusTone === "success" ? palette.green : palette.textMuted, marginTop: 10, marginBottom: 0, lineHeight: 1.6 }}>
                {status}
              </p>
            </div>
          </div>
          <div style={{ height: 1, background: palette.line, margin: "24px 0" }} />
          <p style={{ color: statusTone === "error" ? palette.red : statusTone === "success" ? palette.green : palette.textMuted, marginTop: 0 }}>
            {status}
          </p>
          {summary ? (
            <>
              <ProjectSelector
                summary={summary}
                selectedProject={selectedProject}
                setSelectedProject={setSelectedProject}
                promoteAllProjects={promoteAllProjects}
                setPromoteAllProjects={setPromoteAllProjects}
              />
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 14, marginTop: 22 }}>
                <MetricCard label="Local Rules" value={summary.overview.local_rules} />
                <MetricCard label="Global Rules" value={summary.overview.global_rules} />
                <MetricCard label="Merged Rules" value={summary.overview.merged_rules} />
                <MetricCard label="Curated Merged" value={((summary.merged.rules as Record<string, unknown>[]) ?? []).filter((rule) => !isLowSignalDraft(rule)).length} />
                <MetricCard label="Candidates" value={summary.overview.candidates} />
                <MetricCard label="Local History" value={summary.overview.local_history_entries} />
                <MetricCard label="Global History" value={summary.overview.global_history_entries} />
              </div>
            </>
          ) : null}
        </section>

        {summary ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 18, marginTop: 24 }}>
            <CountList title="History by Action" data={summary.history_summary.by_action} />
            <CountList title="History by Adapter" data={summary.history_summary.by_adapter} />
            <CountList title="History by Decision" data={summary.history_summary.by_decision} />
          </div>
        ) : null}

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20, marginTop: 24, alignItems: "start" }}>
          <RulesPanel
            scope={scope}
            setScope={setScope}
            rules={rules}
            counts={ruleCounts}
            onPromoteGlobal={promoteGlobal}
            selectedRuleName={selectedRuleName}
            onSelectRule={setSelectedRuleName}
            disabled={actionPending}
          />
          <CandidatesPanel
            candidates={summary?.candidates ?? []}
            onReviewCandidate={reviewCandidate}
            selectedCandidatePath={selectedCandidatePath}
            onSelectCandidate={setSelectedCandidatePath}
            disabled={actionPending}
          />
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 20, marginTop: 24, alignItems: "start" }}>
          <RuleDetailPanel rule={selectedRule} onPromoteGlobal={promoteGlobal} disabled={actionPending} />
          <CandidateDetailPanel candidate={selectedCandidate} onReviewCandidate={reviewCandidate} disabled={actionPending} />
        </div>
        <HistoryTable items={summary?.recent_history ?? []} filter={historyFilter} setFilter={setHistoryFilter} />
      </div>
    </div>
  );
}
