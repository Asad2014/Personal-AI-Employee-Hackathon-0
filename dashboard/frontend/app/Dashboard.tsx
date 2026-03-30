"use client";
import { useState, useEffect, useCallback } from "react";
import Sidebar from "./components/Sidebar";
import StatCard from "./components/StatCard";
import AlertBanner from "./components/AlertBanner";
import ActivityChart from "./components/ActivityChart";
import FileModal from "./components/FileModal";
import { api, Stats, VaultFile, LogEntry, Alert, ChartData } from "./lib/api";

// ── Helpers ──────────────────────────────────────────────────────────────────

const TYPE_BADGE: Record<string, string> = {
  email: "badge-blue", approval_request: "badge-yellow",
  linkedin_post: "badge-purple", twitter_post: "badge-blue",
  facebook_post: "badge-blue",  instagram_post: "badge-purple",
  task: "badge-green", whatsapp: "badge-green", general: "badge-gray",
};

const PRIORITY_BADGE: Record<string, string> = {
  high: "badge-red", medium: "badge-yellow", low: "badge-gray",
};

const ACTION_COLOR: Record<string, string> = {
  email_detected: "#3b82f6", email_reply: "#10b981",
  claude_processing_run: "#8b5cf6", approval: "#f59e0b",
  post_published: "#10b981",
};

function timeSince(iso: string) {
  try {
    const diff = Date.now() - new Date(iso).getTime();
    const m = Math.floor(diff / 60000);
    if (m < 1)  return "just now";
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    return `${Math.floor(h / 24)}d ago`;
  } catch { return ""; }
}

function sectionTitle(title: string, count?: number) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
      <h2 style={{ fontSize: 16, fontWeight: 700, color: "var(--text-primary)" }}>{title}</h2>
      {count !== undefined && (
        <span style={{
          background: "var(--bg-hover)", color: "var(--text-muted)",
          borderRadius: 999, padding: "1px 8px", fontSize: 12,
        }}>{count}</span>
      )}
    </div>
  );
}

// ── File Row ─────────────────────────────────────────────────────────────────
function FileRow({
  file, onClick, actions,
}: {
  file: VaultFile;
  onClick: () => void;
  actions?: React.ReactNode;
}) {
  return (
    <div
      onClick={onClick}
      style={{
        display: "flex", alignItems: "center", gap: 12,
        padding: "11px 16px",
        borderBottom: "1px solid var(--border)",
        cursor: "pointer",
        transition: "background 0.15s",
      }}
      onMouseEnter={e => (e.currentTarget.style.background = "var(--bg-hover)")}
      onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
    >
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 13, fontWeight: 500, color: "var(--text-primary)",
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
        }}>
          {file.meta?.requested_action || file.meta?.subject ||
           file.filename.replace(/\.(md)$/, "").replace(/_/g, " ")}
        </div>
        <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>
          {timeSince(file.modified)} · {file.filename}
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
        <span className={`badge ${TYPE_BADGE[file.type] ?? "badge-gray"}`}>{file.type}</span>
        {file.priority && file.priority !== "medium" && (
          <span className={`badge ${PRIORITY_BADGE[file.priority] ?? "badge-gray"}`}>{file.priority}</span>
        )}
        {actions}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function Dashboard() {
  const [view, setView]             = useState("overview");
  const [stats, setStats]           = useState<Stats | null>(null);
  const [pending, setPending]       = useState<VaultFile[]>([]);
  const [inbox, setInbox]           = useState<VaultFile[]>([]);
  const [done, setDone]             = useState<VaultFile[]>([]);
  const [logs, setLogs]             = useState<LogEntry[]>([]);
  const [alerts, setAlerts]         = useState<Alert[]>([]);
  const [chart, setChart]           = useState<ChartData>({ labels: [], values: [] });
  const [selected, setSelected]     = useState<VaultFile | null>(null);
  const [showApproveActions, setShowApproveActions] = useState(false);
  const [lastRefresh, setLastRefresh] = useState<string>("");

  const loadAll = useCallback(async () => {
    try {
      const [s, p, ib, d, l, al, ch] = await Promise.all([
        api.stats(), api.pending(), api.inbox(), api.done(),
        api.logs(), api.alerts(), api.chart(),
      ]);
      setStats(s);
      setPending(p.items);
      setInbox(ib.items);
      setDone(d.items);
      setLogs(l.entries);
      setAlerts(al.alerts);
      setChart(ch);
      setLastRefresh(new Date().toLocaleTimeString());
    } catch (_) {}
  }, []);

  useEffect(() => {
    loadAll();
    const t = setInterval(loadAll, 30000);
    return () => clearInterval(t);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleApprove = async (filename: string) => {
    await api.approve(filename);
    await loadAll();
  };

  const handleReject = async (filename: string) => {
    await api.reject(filename);
    await loadAll();
  };

  const openFile = (file: VaultFile, withActions = false) => {
    setSelected(file);
    setShowApproveActions(withActions);
  };

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <Sidebar
        active={view}
        onNav={setView}
        pendingCount={pending.length}
        inboxCount={inbox.length}
      />

      {/* Main */}
      <div style={{ flex: 1, overflow: "auto", background: "var(--bg-primary)" }}>

        {/* Top Bar */}
        <div style={{
          padding: "16px 28px",
          borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center", justifyContent: "space-between",
          background: "var(--bg-secondary)",
          position: "sticky", top: 0, zIndex: 10,
        }}>
          <div>
            <h1 style={{ fontSize: 17, fontWeight: 700, color: "var(--text-primary)" }}>
              {view === "overview"  && "Overview"}
              {view === "inbox"     && "Inbox — Needs Action"}
              {view === "approvals" && "Pending Approvals"}
              {view === "done"      && "Completed Tasks"}
              {view === "logs"      && "Activity Logs"}
            </h1>
            <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
              {lastRefresh ? `Last refreshed: ${lastRefresh}` : "Connecting…"}
            </div>
          </div>
          <button
            onClick={loadAll}
            style={{
              background: "var(--bg-hover)", border: "1px solid var(--border)",
              color: "var(--text-dim)", borderRadius: 8,
              padding: "7px 14px", cursor: "pointer", fontSize: 13, fontWeight: 500,
            }}
          >⟳ Refresh</button>
        </div>

        <div style={{ padding: "24px 28px" }}>

          {/* ── OVERVIEW ─────────────────────────────────────────────────── */}
          {view === "overview" && stats && (
            <div className="slide-in">
              <AlertBanner
                alerts={alerts}
                onDismiss={(level) => setAlerts(prev => prev.filter(a => a.level !== level))}
              />

              {/* Stats Grid */}
              <div style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
                gap: 14, marginBottom: 28,
              }}>
                <StatCard label="Needs Action"    value={stats.needs_action} icon="📬" color="#3b82f6" />
                <StatCard label="Pending Approval" value={stats.pending}     icon="⏳" color="#f59e0b" />
                <StatCard label="Completed"        value={stats.done}        icon="✅" color="#10b981" />
                <StatCard label="In Progress"      value={stats.in_progress} icon="⚡" color="#8b5cf6" />
                <StatCard label="Plans"            value={stats.plans}       icon="🗺" color="#06b6d4" />
                <StatCard label="Briefings"        value={stats.briefings}   icon="📊" color="#ec4899" />
                <StatCard label="Approved"         value={stats.approved}    icon="✓"  color="#10b981" />
                <StatCard label="Rejected"         value={stats.rejected}    icon="✗"  color="#ef4444" />
              </div>

              {/* Two columns */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>

                {/* Activity Chart */}
                <div style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: 12, padding: "18px 20px",
                }}>
                  {sectionTitle("Activity — Last 7 Days")}
                  <ActivityChart data={chart} />
                </div>

                {/* Recent Pending */}
                <div style={{
                  background: "var(--bg-card)",
                  border: "1px solid var(--border)",
                  borderRadius: 12, overflow: "hidden",
                }}>
                  <div style={{ padding: "18px 20px 14px" }}>
                    {sectionTitle("Pending Approvals", pending.length)}
                  </div>
                  {pending.length === 0 ? (
                    <div style={{ padding: "0 20px 20px", color: "var(--text-muted)", fontSize: 13 }}>
                      Nothing pending — all clear!
                    </div>
                  ) : (
                    pending.slice(0, 5).map(f => (
                      <FileRow
                        key={f.filename}
                        file={f}
                        onClick={() => openFile(f, true)}
                        actions={
                          <div style={{ display: "flex", gap: 6 }} onClick={e => e.stopPropagation()}>
                            <button
                              onClick={() => handleApprove(f.filename)}
                              style={{
                                background: "rgba(16,185,129,0.15)", border: "1px solid rgba(16,185,129,0.3)",
                                color: "#34d399", borderRadius: 6, padding: "3px 10px",
                                cursor: "pointer", fontSize: 12, fontWeight: 600,
                              }}>✓</button>
                            <button
                              onClick={() => handleReject(f.filename)}
                              style={{
                                background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.25)",
                                color: "#f87171", borderRadius: 6, padding: "3px 10px",
                                cursor: "pointer", fontSize: 12, fontWeight: 600,
                              }}>✗</button>
                          </div>
                        }
                      />
                    ))
                  )}
                </div>
              </div>

              {/* Recent Logs */}
              <div style={{
                marginTop: 20,
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: 12, padding: "18px 20px",
              }}>
                {sectionTitle("Recent Activity")}
                <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                  {logs.slice(0, 8).map((entry, i) => (
                    <div key={i} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                      <div style={{
                        width: 6, height: 6, borderRadius: "50%", flexShrink: 0, marginTop: 6,
                        background: ACTION_COLOR[entry.action_type] ?? "#64748b",
                      }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <span style={{ color: "var(--text-primary)", fontSize: 13 }}>
                          {entry.action_type.replace(/_/g, " ")}
                        </span>
                        {" · "}
                        <span style={{ color: "var(--text-muted)", fontSize: 12 }}>
                          {entry.target}
                        </span>
                      </div>
                      <div style={{ color: "var(--text-muted)", fontSize: 11, flexShrink: 0 }}>
                        {timeSince(entry.timestamp)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* ── INBOX ────────────────────────────────────────────────────── */}
          {view === "inbox" && (
            <div className="slide-in">
              <div style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: 12, overflow: "hidden",
              }}>
                {sectionTitle("Items Awaiting Processing", inbox.length)}
                {inbox.length === 0 ? (
                  <div style={{ padding: "24px", color: "var(--text-muted)", fontSize: 13, textAlign: "center" }}>
                    Inbox is empty — all items have been processed.
                  </div>
                ) : (
                  inbox.map(f => (
                    <FileRow key={f.filename} file={f} onClick={() => openFile(f, false)} />
                  ))
                )}
              </div>
            </div>
          )}

          {/* ── APPROVALS ────────────────────────────────────────────────── */}
          {view === "approvals" && (
            <div className="slide-in">
              <div style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: 12, overflow: "hidden",
              }}>
                <div style={{ padding: "18px 20px 0" }}>
                  {sectionTitle("Awaiting Your Approval", pending.length)}
                </div>
                {pending.length === 0 ? (
                  <div style={{ padding: "24px", color: "var(--text-muted)", fontSize: 13, textAlign: "center" }}>
                    No items pending approval.
                  </div>
                ) : (
                  pending.map(f => (
                    <FileRow
                      key={f.filename}
                      file={f}
                      onClick={() => openFile(f, true)}
                      actions={
                        <div style={{ display: "flex", gap: 8 }} onClick={e => e.stopPropagation()}>
                          <button
                            onClick={() => handleApprove(f.filename)}
                            style={{
                              background: "linear-gradient(135deg,#10b981,#059669)",
                              border: "none", color: "#fff", borderRadius: 7,
                              padding: "5px 14px", cursor: "pointer", fontSize: 12, fontWeight: 600,
                            }}>Approve</button>
                          <button
                            onClick={() => handleReject(f.filename)}
                            style={{
                              background: "rgba(239,68,68,0.12)", border: "1px solid rgba(239,68,68,0.3)",
                              color: "#f87171", borderRadius: 7, padding: "5px 14px",
                              cursor: "pointer", fontSize: 12, fontWeight: 600,
                            }}>Reject</button>
                        </div>
                      }
                    />
                  ))
                )}
              </div>
            </div>
          )}

          {/* ── DONE ─────────────────────────────────────────────────────── */}
          {view === "done" && (
            <div className="slide-in">
              <div style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: 12, overflow: "hidden",
              }}>
                <div style={{ padding: "18px 20px 0" }}>
                  {sectionTitle("Completed Tasks", done.length)}
                </div>
                {done.map(f => (
                  <FileRow key={f.filename} file={f} onClick={() => openFile(f, false)} />
                ))}
              </div>
            </div>
          )}

          {/* ── LOGS ─────────────────────────────────────────────────────── */}
          {view === "logs" && (
            <div className="slide-in">
              <div style={{
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: 12, padding: "18px 20px",
              }}>
                {sectionTitle("Activity Logs", logs.length)}
                <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
                  {logs.map((entry, i) => (
                    <div key={i} style={{
                      display: "flex", gap: 16, padding: "10px 0",
                      borderBottom: "1px solid var(--border)",
                      alignItems: "flex-start",
                    }}>
                      {/* Color dot */}
                      <div style={{
                        width: 8, height: 8, borderRadius: "50%", flexShrink: 0, marginTop: 5,
                        background: ACTION_COLOR[entry.action_type] ?? "#64748b",
                      }} />
                      {/* Content */}
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
                          <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                            {entry.action_type.replace(/_/g, " ")}
                          </span>
                          <span className={`badge ${entry.result === "success" ? "badge-green" : "badge-red"}`}>
                            {entry.result}
                          </span>
                          {entry.approval_status !== "n/a" && (
                            <span className="badge badge-gray">{entry.approval_status}</span>
                          )}
                        </div>
                        <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 2 }}>
                          <span style={{ color: "#60a5fa" }}>{entry.actor}</span>
                          {" → "}
                          {entry.target}
                        </div>
                      </div>
                      {/* Time */}
                      <div style={{ fontSize: 11, color: "var(--text-muted)", flexShrink: 0, whiteSpace: "nowrap" }}>
                        {entry.timestamp.slice(0, 19).replace("T", " ")}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

        </div>
      </div>

      {/* File Detail Modal */}
      <FileModal
        file={selected}
        onClose={() => setSelected(null)}
        onApprove={handleApprove}
        onReject={handleReject}
        showActions={showApproveActions}
      />
    </div>
  );
}
