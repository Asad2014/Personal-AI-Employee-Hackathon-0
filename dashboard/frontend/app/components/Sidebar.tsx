"use client";
import { useState } from "react";

const navItems = [
  { id: "overview",  label: "Overview",       icon: "⊡" },
  { id: "inbox",     label: "Inbox",           icon: "✉" },
  { id: "approvals", label: "Approvals",       icon: "✓" },
  { id: "done",      label: "Completed",       icon: "◎" },
  { id: "logs",      label: "Activity Logs",   icon: "≡" },
];

interface SidebarProps {
  active: string;
  onNav: (id: string) => void;
  pendingCount: number;
  inboxCount: number;
}

export default function Sidebar({ active, onNav, pendingCount, inboxCount }: SidebarProps) {
  return (
    <aside style={{
      width: 220,
      minHeight: "100vh",
      background: "var(--bg-secondary)",
      borderRight: "1px solid var(--border)",
      display: "flex",
      flexDirection: "column",
      flexShrink: 0,
    }}>
      {/* Logo */}
      <div style={{
        padding: "24px 20px 20px",
        borderBottom: "1px solid var(--border)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 32, height: 32, borderRadius: 8,
            background: "linear-gradient(135deg, #3b82f6, #8b5cf6)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 16, flexShrink: 0,
          }}>🤖</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 13, color: "var(--text-primary)" }}>AI Employee</div>
            <div style={{ fontSize: 11, color: "var(--text-muted)" }}>Control Center</div>
          </div>
        </div>
      </div>

      {/* Status pill */}
      <div style={{ padding: "12px 16px" }}>
        <div style={{
          background: "rgba(16,185,129,0.1)",
          border: "1px solid rgba(16,185,129,0.2)",
          borderRadius: 8,
          padding: "8px 12px",
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <span className="pulse-dot" style={{
            width: 7, height: 7, borderRadius: "50%",
            background: "#10b981", display: "inline-block", flexShrink: 0,
          }} />
          <span style={{ fontSize: 12, color: "#34d399", fontWeight: 500 }}>Operational</span>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ padding: "8px 10px", flex: 1 }}>
        {navItems.map(item => {
          const isActive = active === item.id;
          const badge = item.id === "approvals" ? pendingCount :
                        item.id === "inbox"     ? inboxCount   : 0;
          return (
            <button
              key={item.id}
              onClick={() => onNav(item.id)}
              style={{
                width: "100%",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "9px 12px",
                marginBottom: 2,
                borderRadius: 8,
                border: "none",
                cursor: "pointer",
                background: isActive ? "rgba(59,130,246,0.15)" : "transparent",
                color: isActive ? "#60a5fa" : "var(--text-dim)",
                fontWeight: isActive ? 600 : 400,
                fontSize: 13,
                transition: "all 0.15s",
                textAlign: "left",
              }}
              onMouseEnter={e => {
                if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = "var(--bg-hover)";
              }}
              onMouseLeave={e => {
                if (!isActive) (e.currentTarget as HTMLButtonElement).style.background = "transparent";
              }}
            >
              <span style={{ display: "flex", alignItems: "center", gap: 9 }}>
                <span style={{ fontSize: 15, opacity: 0.8 }}>{item.icon}</span>
                {item.label}
              </span>
              {badge > 0 && (
                <span style={{
                  background: item.id === "approvals" ? "#f59e0b" : "#3b82f6",
                  color: "#000",
                  borderRadius: 999,
                  padding: "1px 7px",
                  fontSize: 11,
                  fontWeight: 700,
                  minWidth: 20,
                  textAlign: "center",
                }}>{badge}</span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer */}
      <div style={{
        padding: "14px 16px",
        borderTop: "1px solid var(--border)",
        fontSize: 11,
        color: "var(--text-muted)",
      }}>
        <div>v0.1 — Powered by Claude</div>
      </div>
    </aside>
  );
}
