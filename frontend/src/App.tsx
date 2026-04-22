import React, { useEffect, useMemo, useState } from "react";
import { CandidateDetailPanel, CandidatesPanel, CountList, HistoryTable, MetricCard, ProjectSelector, RuleDetailPanel, RulesPanel } from "./components";
import { Summary, pageStyle, panelStyle } from "./types";

export function App() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [scope, setScope] = useState<"merged" | "local" | "global">("merged");
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
    setSelectedRuleName((prev) => prev || String(json.merged.rules[0]?.name ?? ""));
    setSelectedCandidatePath((prev) => prev || String(json.candidates[0]?.path ?? ""));
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
        body: JSON.stringify({ name, all_projects: promoteAllProjects }),
      });
      if (!res.ok) throw new Error(await res.text());
      await load();
      setStatus(`Promoted ${name} to global brain.`);
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
        body: JSON.stringify({ candidate, action }),
      });
      if (!res.ok) throw new Error(await res.text());
      await load();
      setStatus(`Candidate action complete: ${action}.`);
      setStatusTone("success");
    } catch (err) {
      setStatus(String(err));
      setStatusTone("error");
    } finally {
      setActionPending(false);
    }
  }

  const rules = useMemo(() => (summary ? summary[scope].rules : []), [summary, scope]);
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
      <div style={{ maxWidth: 1280, margin: "0 auto", padding: 24 }}>
        <section style={{ ...panelStyle, borderRadius: 22, padding: 24 }}>
          <h1 style={{ marginTop: 0, marginBottom: 8 }}>agent-learner dashboard</h1>
          <p style={{ color: statusTone === "error" ? "#b85c38" : statusTone === "success" ? "#0d6b5f" : "#56636b", marginTop: 0 }}>
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
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginTop: 18 }}>
                <MetricCard label="Local Rules" value={summary.overview.local_rules} />
                <MetricCard label="Global Rules" value={summary.overview.global_rules} />
                <MetricCard label="Merged Rules" value={summary.overview.merged_rules} />
                <MetricCard label="Candidates" value={summary.overview.candidates} />
                <MetricCard label="Local History" value={summary.overview.local_history_entries} />
                <MetricCard label="Global History" value={summary.overview.global_history_entries} />
              </div>
            </>
          ) : null}
        </section>

        {summary ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 14, marginTop: 18 }}>
            <CountList title="History by Action" data={summary.history_summary.by_action} />
            <CountList title="History by Adapter" data={summary.history_summary.by_adapter} />
            <CountList title="History by Decision" data={summary.history_summary.by_decision} />
          </div>
        ) : null}

        <div style={{ display: "grid", gridTemplateColumns: "1.1fr .9fr", gap: 18, marginTop: 18 }}>
          <RulesPanel
            scope={scope}
            setScope={setScope}
            rules={rules}
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
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 18, marginTop: 18 }}>
          <RuleDetailPanel rule={selectedRule} onPromoteGlobal={promoteGlobal} disabled={actionPending} />
          <CandidateDetailPanel candidate={selectedCandidate} onReviewCandidate={reviewCandidate} disabled={actionPending} />
        </div>
        <HistoryTable items={summary?.recent_history ?? []} filter={historyFilter} setFilter={setHistoryFilter} />
      </div>
    </div>
  );
}
