import csv, io, json, re, sqlite3
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from .scoring import score_lead

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "leads.db"
app = FastAPI(title="Target Triage")

def db():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS leads(key TEXT PRIMARY KEY, data TEXT, score INT, tier TEXT, reasons TEXT)")
    return c

def norm(s):
    return re.sub(r"\W+", "", str(s).lower().replace("&", "and"))

def import_csv(text):
    rows = list(csv.DictReader(io.StringIO(text)))
    c, seen, dupes = db(), set(), 0
    for r in rows:
        r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
        if not r.get("name"):
            continue
        key = norm(r["name"]) + "|" + norm(r.get("city", ""))
        if key in seen:
            dupes += 1; continue
        seen.add(key)
        s, tier, why = score_lead(r)
        c.execute("INSERT OR REPLACE INTO leads VALUES(?,?,?,?,?)", (key, json.dumps(r), s, tier, json.dumps(why)))
    c.commit(); c.close()
    return {"imported": len(seen), "duplicates_removed": dupes}

def all_leads():
    c = db()
    out = [{**json.loads(d), "score": s, "tier": t, "reasons": json.loads(w)}
           for d, s, t, w in c.execute("SELECT data,score,tier,reasons FROM leads ORDER BY score DESC")]
    c.close()
    return out

class Upload(BaseModel):
    csv: str

@app.post("/api/import")
def api_import(u: Upload):
    return import_csv(u.csv)

@app.post("/api/sample")
def api_sample():
    return import_csv((ROOT / "sample_leads.csv").read_text())

@app.get("/api/leads")
def api_leads():
    return all_leads()

@app.delete("/api/leads")
def api_clear():
    c = db(); c.execute("DELETE FROM leads"); c.commit(); c.close()
    return {"ok": True}

@app.get("/api/export")
def api_export():
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["name", "city", "industry", "score", "tier", "why"])
    for l in all_leads():
        w.writerow([l["name"], l.get("city", ""), l.get("industry", ""), l["score"], l["tier"], "; ".join(l["reasons"])])
    return PlainTextResponse(buf.getvalue(), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=ranked_targets.csv"})

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

@app.get("/")
def index():
    return FileResponse(Path(__file__).parent / "static" / "index.html")
