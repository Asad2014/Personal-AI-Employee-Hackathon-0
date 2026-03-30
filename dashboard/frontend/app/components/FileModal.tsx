"use client";
import { useEffect, useState } from "react";
import { api, VaultFile } from "../lib/api";

interface FileModalProps {
  file: VaultFile | null;
  onClose: () => void;
  onApprove?: (filename: string) => void;
  onReject?: (filename: string) => void;
  showActions?: boolean;
}

const TYPE_BADGE: Record<string, string> = {
  email:            "badge-blue",
  approval_request: "badge-yellow",
  linkedin_post:    "badge-purple",
  twitter_post:     "badge-blue",
  facebook_post:    "badge-blue",
  instagram_post:   "badge-purple",
  task:             "badge-green",
  whatsapp:         "badge-green",
  general:          "badge-gray",
};

export default function FileModal({ file, onClose, onApprove, onReject, showActions }: FileModalProps) {
  const [fullBody, setFullBody] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!file) return;
    setFullBody(file.body);
    if (file.relative_path) {
      setLoading(true);
      api.file(file.relative_path)
        .then(d => setFullBody(d.body))
        .catch(() => {})
        .finally(() => setLoading(false));
    }
  }, [file]);

  if (!file) return null;

  const badgeClass = TYPE_BADGE[file.type] ?? "badge-gray";

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 50,
        background: "rgba(0,0,0,0.7)",
        display: "flex", alignItems: "center", justifyContent: "center",
        backdropFilter: "blur(4px)",
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        className="slide-in"
        style={{
          background: "var(--bg-card)",
          border: "1px solid var(--border)",
          borderRadius: 16,
          width: "min(700px, 95vw)",
          maxHeight: "85vh",
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <div style={{
          padding: "16px 20px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 12,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
            <span className={`badge ${badgeClass}`}>{file.type}</span>
            <span style={{
              fontSize: 13, color: "var(--text-primary)", fontWeight: 500,
              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
            }}>
              {file.filename}
            </span>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "none", border: "none", color: "var(--text-muted)",
              cursor: "pointer", fontSize: 20, lineHeight: 1, flexShrink: 0,
              padding: "2px 6px", borderRadius: 4,
            }}
          >×</button>
        </div>

        {/* Meta */}
        {Object.keys(file.meta).length > 0 && (
          <div style={{
            padding: "12px 20px",
            borderBottom: "1px solid var(--border)",
            display: "flex", flexWrap: "wrap", gap: 8,
          }}>
            {Object.entries(file.meta).map(([k, v]) => (
              <div key={k} style={{
                background: "var(--bg-hover)",
                borderRadius: 6,
                padding: "3px 10px",
                fontSize: 12,
                color: "var(--text-dim)",
              }}>
                <span style={{ color: "var(--text-muted)" }}>{k}: </span>
                <span>{v}</span>
              </div>
            ))}
          </div>
        )}

        {/* Body */}
        <div style={{
          padding: "16px 20px",
          overflow: "auto",
          flex: 1,
          fontSize: 13,
          color: "var(--text-dim)",
          lineHeight: 1.7,
          whiteSpace: "pre-wrap",
        }}>
          {loading ? (
            <div style={{ color: "var(--text-muted)", fontStyle: "italic" }}>Loading…</div>
          ) : fullBody}
        </div>

        {/* Actions */}
        {showActions && onApprove && onReject && (
          <div style={{
            padding: "14px 20px",
            borderTop: "1px solid var(--border)",
            display: "flex", gap: 10, justifyContent: "flex-end",
          }}>
            <button
              onClick={() => { onReject(file.filename); onClose(); }}
              style={{
                padding: "8px 20px", borderRadius: 8, border: "1px solid rgba(239,68,68,0.3)",
                background: "rgba(239,68,68,0.1)", color: "#f87171",
                cursor: "pointer", fontWeight: 600, fontSize: 13,
              }}
            >✗ Reject</button>
            <button
              onClick={() => { onApprove(file.filename); onClose(); }}
              style={{
                padding: "8px 20px", borderRadius: 8, border: "none",
                background: "linear-gradient(135deg, #10b981, #059669)",
                color: "#fff", cursor: "pointer", fontWeight: 600, fontSize: 13,
              }}
            >✓ Approve</button>
          </div>
        )}
      </div>
    </div>
  );
}
