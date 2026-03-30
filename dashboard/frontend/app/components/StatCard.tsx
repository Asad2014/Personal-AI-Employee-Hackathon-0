interface StatCardProps {
  label: string;
  value: number | string;
  icon: string;
  color?: string;
  sublabel?: string;
}

export default function StatCard({ label, value, icon, color = "#3b82f6", sublabel }: StatCardProps) {
  return (
    <div style={{
      background: "var(--bg-card)",
      border: "1px solid var(--border)",
      borderRadius: 12,
      padding: "18px 20px",
      display: "flex",
      flexDirection: "column",
      gap: 8,
      transition: "border-color 0.2s",
    }}
    onMouseEnter={e => (e.currentTarget.style.borderColor = color + "55")}
    onMouseLeave={e => (e.currentTarget.style.borderColor = "var(--border)")}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div style={{
          width: 38, height: 38, borderRadius: 10,
          background: color + "20",
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 18,
        }}>{icon}</div>
      </div>
      <div>
        <div style={{ fontSize: 26, fontWeight: 700, color: "var(--text-primary)", lineHeight: 1.1 }}>
          {value}
        </div>
        <div style={{ fontSize: 12, color: "var(--text-muted)", marginTop: 3 }}>{label}</div>
        {sublabel && (
          <div style={{ fontSize: 11, color: color, marginTop: 3, fontWeight: 500 }}>{sublabel}</div>
        )}
      </div>
    </div>
  );
}
