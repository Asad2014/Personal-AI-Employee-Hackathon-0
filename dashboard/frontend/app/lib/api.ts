const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface VaultFile {
  filename: string;
  relative_path: string;
  meta: Record<string, string>;
  body: string;
  modified: string;
  type: string;
  status: string;
  priority: string;
  error?: string;
}

export interface Stats {
  inbox: number;
  needs_action: number;
  pending: number;
  approved: number;
  rejected: number;
  plans: number;
  done: number;
  briefings: number;
  in_progress: number;
  system_status: string;
  last_updated: string;
}

export interface LogEntry {
  timestamp: string;
  action_type: string;
  actor: string;
  target: string;
  approval_status: string;
  result: string;
  parameters?: Record<string, unknown>;
}

export interface Alert {
  level: string;
  message: string;
  severity: "error" | "warning" | "info";
}

export interface ChartData {
  labels: string[];
  values: number[];
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

async function post<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { method: "POST", cache: "no-store" });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json();
}

export const api = {
  stats:   () => get<Stats>("/api/stats"),
  pending: () => get<{ items: VaultFile[]; count: number }>("/api/pending"),
  inbox:   () => get<{ items: VaultFile[]; count: number }>("/api/inbox"),
  done:    () => get<{ items: VaultFile[]; count: number }>("/api/done"),
  logs:    () => get<{ entries: LogEntry[]; count: number }>("/api/logs"),
  alerts:  () => get<{ alerts: Alert[]; count: number }>("/api/alerts"),
  chart:   () => get<ChartData>("/api/chart"),
  approve:        (filename: string) => post<{ status: string }>(`/api/approve/${encodeURIComponent(filename)}`),
  reject:         (filename: string) => post<{ status: string }>(`/api/reject/${encodeURIComponent(filename)}`),
  dismissAlert:   (level: string) => fetch(`${API}/api/alerts?level=${encodeURIComponent(level)}`, { method: "DELETE", cache: "no-store" }).then(r => r.json()),
  file:           (path: string) => get<{ filename: string; meta: Record<string,string>; body: string }>(`/api/file?path=${encodeURIComponent(path)}`),
};
