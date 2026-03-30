"use client";
import { Alert, api } from "../lib/api";

const severityStyles: Record<string, { bg: string; border: string; color: string; icon: string }> = {
  error:   { bg: "rgba(239,68,68,0.08)",   border: "rgba(239,68,68,0.25)",   color: "#f87171", icon: "⚠" },
  warning: { bg: "rgba(245,158,11,0.08)",  border: "rgba(245,158,11,0.25)",  color: "#fbbf24", icon: "⚡" },
  info:    { bg: "rgba(59,130,246,0.08)",  border: "rgba(59,130,246,0.25)",  color: "#60a5fa", icon: "ℹ" },
};

interface AlertBannerProps {
  alerts: Alert[];
  onDismiss: (level: string) => void;
}

export default function AlertBanner({ alerts, onDismiss }: AlertBannerProps) {
  if (!alerts.length) return null;

  const handleDismiss = async (level: string) => {
    try {
      await api.dismissAlert(level);
      onDismiss(level);
    } catch (_) {}
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 24 }}>
      {alerts.map((a, i) => {
        const s = severityStyles[a.severity] ?? severityStyles.info;
        return (
          <div key={i} className="slide-in" style={{
            background: s.bg,
            border: `1px solid ${s.border}`,
            borderRadius: 10,
            padding: "10px 16px",
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}>
            <span style={{ color: s.color, fontSize: 15, flexShrink: 0 }}>{s.icon}</span>
            <div style={{ flex: 1 }}>
              <span style={{ color: s.color, fontWeight: 700, fontSize: 12, marginRight: 6 }}>{a.level}</span>
              <span style={{ color: "var(--text-dim)", fontSize: 13 }}>{a.message}</span>
            </div>
            <button
              onClick={() => handleDismiss(a.level)}
              title="Dismiss alert"
              style={{
                background: "none",
                border: "none",
                color: "var(--text-muted)",
                cursor: "pointer",
                fontSize: 16,
                lineHeight: 1,
                padding: "2px 6px",
                borderRadius: 4,
                flexShrink: 0,
                transition: "color 0.15s",
              }}
              onMouseEnter={e => (e.currentTarget.style.color = s.color)}
              onMouseLeave={e => (e.currentTarget.style.color = "var(--text-muted)")}
            >✕</button>
          </div>
        );
      })}
    </div>
  );
}
