"""
Personal AI Employee — Dashboard API
FastAPI backend that reads the Obsidian vault and exposes REST endpoints.
"""
import os
import re
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ── Config ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent.parent
VAULT = BASE_DIR / "AI_Employee_Vault"

FOLDERS = {
    "inbox":        VAULT / "Inbox",
    "needs_action": VAULT / "Needs_Action",
    "pending":      VAULT / "Pending_Approval",
    "approved":     VAULT / "Approved",
    "rejected":     VAULT / "Rejected",
    "plans":        VAULT / "Plans",
    "done":         VAULT / "Done",
    "logs":         VAULT / "Logs",
    "briefings":    VAULT / "Briefings",
    "in_progress":  VAULT / "In_Progress",
}

app = FastAPI(title="AI Employee Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def parse_frontmatter(text: str) -> tuple[dict, str]:
    meta = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            for line in parts[1].strip().splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    meta[key.strip()] = val.strip().strip('"').strip("'")
            body = parts[2].strip()
    return meta, body


def count_files(folder: Path) -> int:
    if not folder.exists():
        return 0
    return len([f for f in folder.rglob("*.md")])


def _infer_type(name: str) -> str:
    n = name.lower()
    if n.startswith("email"):     return "email"
    if n.startswith("linkedin"):  return "linkedin_post"
    if n.startswith("twitter"):   return "twitter_post"
    if n.startswith("facebook"):  return "facebook_post"
    if n.startswith("instagram"): return "instagram_post"
    if n.startswith("approval"):  return "approval_request"
    if n.startswith("task"):      return "task"
    if n.startswith("whatsapp"):  return "whatsapp"
    return "general"


def read_vault_file(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        return {
            "filename": path.name,
            "relative_path": str(path.relative_to(VAULT)),
            "meta": meta,
            "body": body[:500] + ("…" if len(body) > 500 else ""),
            "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "type": meta.get("type", _infer_type(path.name)),
            "status": meta.get("status", "pending"),
            "priority": meta.get("priority", "medium"),
        }
    except Exception as e:
        return {"filename": path.name, "error": str(e)}


def list_folder(folder: Path) -> list[dict]:
    if not folder.exists():
        return []
    files = sorted(folder.rglob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    return [read_vault_file(f) for f in files]


def parse_alerts() -> list[dict]:
    dash = VAULT / "Dashboard.md"
    alerts = []
    if not dash.exists():
        return alerts
    text = dash.read_text(encoding="utf-8")
    in_alerts = False
    for line in text.splitlines():
        if line.strip().startswith("## Alerts"):
            in_alerts = True
            continue
        if in_alerts:
            if line.startswith("## "):
                break
            m = re.match(r"- \*\*(\w+):\*\*\s*(.*)", line)
            if m:
                level = m.group(1).upper()
                severity = "error"   if level in ("SECURITY", "OVERDUE") else \
                           "warning" if level in ("STALE", "TOKEN")       else "info"
                alerts.append({"level": level, "message": m.group(2), "severity": severity})
    return alerts


def read_recent_logs(limit: int = 50) -> list[dict]:
    entries = []
    log_files = sorted(FOLDERS["logs"].glob("*.json"), reverse=True)[:5]
    for lf in log_files:
        try:
            for line in lf.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass
    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return entries[:limit]


def get_chart_data() -> dict:
    from collections import defaultdict
    counts = defaultdict(int)
    log_files = sorted(FOLDERS["logs"].glob("*.json"), reverse=True)[:7]
    for lf in log_files:
        try:
            lines = [l for l in lf.read_text(encoding="utf-8").splitlines() if l.strip()]
            counts[lf.stem] = len(lines)
        except Exception:
            pass
    days = sorted(counts.keys())[-7:]
    return {"labels": days, "values": [counts[d] for d in days]}


def append_log(action_type: str, actor: str, target: str, approval_status: str, result: str):
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = FOLDERS["logs"] / f"{today}.json"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "action_type": action_type,
        "actor": actor,
        "target": target,
        "approval_status": approval_status,
        "result": result,
    }
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def find_file(folder: Path, filename: str) -> Optional[Path]:
    for f in folder.rglob(filename):
        return f
    return None


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/stats")
def get_stats():
    return {
        "inbox":        count_files(FOLDERS["inbox"]),
        "needs_action": count_files(FOLDERS["needs_action"]),
        "pending":      count_files(FOLDERS["pending"]),
        "approved":     count_files(FOLDERS["approved"]),
        "rejected":     count_files(FOLDERS["rejected"]),
        "plans":        count_files(FOLDERS["plans"]),
        "done":         count_files(FOLDERS["done"]),
        "briefings":    count_files(FOLDERS["briefings"]),
        "in_progress":  count_files(FOLDERS["in_progress"]),
        "system_status": "Operational",
        "last_updated":  datetime.now().isoformat(),
    }


@app.get("/api/pending")
def get_pending():
    items = list_folder(FOLDERS["pending"])
    return {"items": items, "count": len(items)}


@app.get("/api/inbox")
def get_inbox():
    items = list_folder(FOLDERS["needs_action"])
    return {"items": items, "count": len(items)}


@app.get("/api/done")
def get_done():
    items = list_folder(FOLDERS["done"])
    return {"items": items[:25], "count": len(items)}


@app.get("/api/logs")
def get_logs():
    entries = read_recent_logs(50)
    return {"entries": entries, "count": len(entries)}


@app.get("/api/alerts")
def get_alerts():
    alerts = parse_alerts()
    return {"alerts": alerts, "count": len(alerts)}


@app.delete("/api/alerts")
def dismiss_alert(level: str):
    """Remove an alert line from Dashboard.md by its level keyword."""
    dash = VAULT / "Dashboard.md"
    if not dash.exists():
        raise HTTPException(404, "Dashboard.md not found")
    lines = dash.read_text(encoding="utf-8").splitlines()
    new_lines = [l for l in lines if not re.match(rf"- \*\*{re.escape(level)}:\*\*", l)]
    if len(new_lines) == len(lines):
        raise HTTPException(404, f"Alert '{level}' not found")
    dash.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return {"status": "dismissed", "level": level}


@app.get("/api/chart")
def get_chart():
    return get_chart_data()


@app.post("/api/approve/{filename}")
def approve_item(filename: str):
    src = find_file(FOLDERS["pending"], filename)
    if not src:
        raise HTTPException(404, f"File not found: {filename}")
    FOLDERS["approved"].mkdir(exist_ok=True)
    shutil.move(str(src), str(FOLDERS["approved"] / filename))
    append_log("approval", "dashboard_user", filename, "approved", "success")
    return {"status": "approved", "file": filename}


@app.post("/api/reject/{filename}")
def reject_item(filename: str):
    src = find_file(FOLDERS["pending"], filename)
    if not src:
        raise HTTPException(404, f"File not found: {filename}")
    FOLDERS["rejected"].mkdir(exist_ok=True)
    shutil.move(str(src), str(FOLDERS["rejected"] / filename))
    append_log("approval", "dashboard_user", filename, "rejected", "success")
    return {"status": "rejected", "file": filename}


@app.get("/api/file")
def read_file(path: str):
    target = VAULT / path
    try:
        target.resolve().relative_to(VAULT.resolve())
    except ValueError:
        raise HTTPException(403, "Access denied")
    if not target.exists():
        raise HTTPException(404, "File not found")
    text = target.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    return {"filename": target.name, "meta": meta, "body": body}


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
