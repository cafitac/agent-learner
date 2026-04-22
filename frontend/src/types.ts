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

export const palette = {
  bg: "#f5f5f7",
  bgAccent: "#ffffff",
  text: "#111111",
  textMuted: "#6e6e73",
  line: "rgba(17, 17, 17, 0.08)",
  lineStrong: "rgba(17, 17, 17, 0.12)",
  panel: "rgba(255, 255, 255, 0.82)",
  panelStrong: "#ffffff",
  shadow: "0 24px 60px rgba(15, 23, 42, 0.08)",
  shadowSoft: "0 10px 30px rgba(15, 23, 42, 0.06)",
  blue: "#0071e3",
  blueSoft: "rgba(0, 113, 227, 0.10)",
  red: "#d92d20",
  redSoft: "rgba(217, 45, 32, 0.10)",
  green: "#11845b",
  greenSoft: "rgba(17, 132, 91, 0.10)",
};

export const pageStyle: React.CSSProperties = {
  fontFamily: `-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Segoe UI", sans-serif`,
  margin: 0,
  minHeight: "100vh",
  background: `
    radial-gradient(circle at top left, rgba(0, 113, 227, 0.10), transparent 32%),
    radial-gradient(circle at top right, rgba(17, 132, 91, 0.08), transparent 28%),
    linear-gradient(180deg, ${palette.bgAccent} 0%, ${palette.bg} 48%, #eef2f6 100%)
  `,
  color: palette.text,
};

export const panelStyle: React.CSSProperties = {
  background: palette.panel,
  border: `1px solid ${palette.line}`,
  borderRadius: 28,
  padding: 24,
  boxShadow: palette.shadowSoft,
  backdropFilter: "blur(18px)",
};

export const cardStyle: React.CSSProperties = {
  background: palette.panelStrong,
  border: `1px solid ${palette.line}`,
  borderRadius: 22,
  padding: 18,
  boxShadow: "0 8px 24px rgba(15, 23, 42, 0.04)",
};
