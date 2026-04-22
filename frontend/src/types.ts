export type RuleRecord = Record<string, unknown>;
export type CandidateRecord = Record<string, unknown>;
export type HistoryRecord = Record<string, unknown>;

export type Summary = {
  project: { name: string | null; root: string; current_model: string | null; languages: string[]; frameworks: string[] };
  known_projects: Array<{ name: string; root: string }>;
  overview: {
    local_rules: number;
    global_rules: number;
    merged_rules: number;
    candidates: number;
    local_history_entries: number;
    global_history_entries: number;
    latest_activity: string;
  };
  history_summary: {
    by_action: Record<string, number>;
    by_adapter: Record<string, number>;
    by_decision: Record<string, number>;
  };
  merged: { rules: RuleRecord[] };
  local: { rules: RuleRecord[] };
  global: { rules: RuleRecord[] };
  candidates: CandidateRecord[];
  recent_history: HistoryRecord[];
};

export const pageStyle: React.CSSProperties = {
  fontFamily: "Georgia, serif",
  margin: 0,
  minHeight: "100vh",
  background: "linear-gradient(180deg, #fbf7ef 0%, #f7f2e8 100%)",
  color: "#172126",
};

export const panelStyle: React.CSSProperties = {
  background: "#fffaf1",
  border: "1px solid #d8cfbf",
  borderRadius: 18,
  padding: 18,
};

export const cardStyle: React.CSSProperties = {
  background: "white",
  border: "1px solid #d8cfbf",
  borderRadius: 14,
  padding: 14,
};
