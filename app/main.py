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

ALIASES = {
    "name": ["name", "company", "company_name", "business_name", "business", "organization"],
    "city": ["city", "location", "town", "headquarters"],
    "industry": ["industry", "category", "sector", "type"],
    "year_founded": ["year_founded", "founded", "year_established", "established", "founded_year"],
    "employees": ["employees", "employee_count", "size", "num_employees"],
    "est_revenue": ["est_revenue", "revenue", "estimated_revenue", "annual_revenue"],
    "review_count": ["review_count", "reviews", "num_reviews", "number_of_reviews"],
    "rating": ["rating", "stars", "avg_rating", "average_rating"],
    "website": ["website", "url", "domain", "site", "web"],
    "owner_operated": ["owner_operated", "owner", "owner_run", "owner_managed"],
    "locations": ["locations", "location_count", "number_of_locations", "num_locations"],
}

def hkey(h):
    return re.sub(r"[^a-z0-9]+", "_", (h or "").lower().strip("\ufeff ")).strip("_")

def import_csv(text):
    text = text.lstrip("\ufeff")
    first = text.split("\n", 1)[0]
    delim = max(",;\t", key=first.count)
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)
    cols = [hkey(h) for h in (reader.fieldnames or [])]
    lookup = {}
    for canon, names in ALIASES.items():
        for n in names:
            if n in cols:
                lookup[canon] = n; break
    if "name" not in lookup:
        return {"imported": 0, "duplicates_removed": 0,
                "error": "No company name column found. Your columns: " + ", ".join(reader.fieldnames or ["(none)"]) + ". Rename one to 'name'."}
    c, seen, dupes = db(), set(), 0
    c.execute("DELETE FROM leads")  # each import replaces the previous list
    for raw in reader:
        row = {hkey(k): (v or "").strip() for k, v in raw.items() if k}
        r = {canon: row.get(src, "") for canon, src in lookup.items()}
        if not r["name"]:
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
