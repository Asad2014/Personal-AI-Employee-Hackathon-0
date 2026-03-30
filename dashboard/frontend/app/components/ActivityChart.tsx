"use client";
import { ChartData } from "../lib/api";

export default function ActivityChart({ data }: { data: ChartData }) {
  if (!data.labels.length) {
    return (
      <div style={{ height: 120, display: "flex", alignItems: "center", justifyContent: "center", color: "var(--text-muted)", fontSize: 13 }}>
        No activity data
      </div>
    );
  }

  const max = Math.max(...data.values, 1);

  return (
    <div style={{ padding: "8px 0" }}>
      <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height: 80 }}>
        {data.labels.map((label, i) => {
          const h = (data.values[i] / max) * 70 + 6;
          return (
            <div
              key={label}
              title={`${label}: ${data.values[i]} events`}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 4,
                cursor: "default",
              }}
            >
              <div style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 600 }}>
                {data.values[i] || ""}
              </div>
              <div style={{
                width: "100%",
                height: h,
                borderRadius: "4px 4px 0 0",
                background: `linear-gradient(180deg, #3b82f6, #1d4ed8)`,
                opacity: 0.7 + (data.values[i] / max) * 0.3,
                transition: "height 0.4s ease",
              }} />
            </div>
          );
        })}
      </div>
      <div style={{ display: "flex", gap: 8, marginTop: 6 }}>
        {data.labels.map(label => (
          <div key={label} style={{
            flex: 1, textAlign: "center",
            fontSize: 10, color: "var(--text-muted)",
            overflow: "hidden", textOverflow: "ellipsis",
          }}>
            {label.slice(5)}
          </div>
        ))}
      </div>
    </div>
  );
}
