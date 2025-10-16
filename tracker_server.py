from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import os
import psycopg2
import psycopg2.extras
from contextlib import contextmanager

app = FastAPI(title="TaskMind Tracker", version="1.0.0")

# CORS: allow everything for now (tighten later if you want)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# DB CONNECTION + HELPERS
# -----------------------------

def _connect(url: str):
    """Try SSL first (Render External URL), fallback without SSL (Internal URL)."""
    try:
        return psycopg2.connect(url, sslmode="require")
    except Exception:
        # If it's internal URL or local, sslmode may fail. Try plain.
        return psycopg2.connect(url)

def get_conn():
    """
    Connects using DATABASE_URL. If not set, falls back to individual envs (local).
    Raises immediately on failure so we see clean error in /dbcheck.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        return _connect(url)

    # Local dev fallback (optional defaults)
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "taskmind_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS", "postgres"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )

@contextmanager
def db_cursor():
    """Context manager that gives you a cursor and commits safely."""
    conn = get_conn()
    try:
        cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        yield cur
        conn.commit()
    finally:
        try:
            cur.close()
        except Exception:
            pass
        conn.close()

# -----------------------------
# AUTO MIGRATIONS (idempotent)
# -----------------------------

SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS taskmind;
"""

TABLES_SQL = """
CREATE TABLE IF NOT EXISTS taskmind.outreach_leads (
  id SERIAL PRIMARY KEY,
  name TEXT,
  company TEXT,
  email TEXT,
  niche TEXT,
  status TEXT DEFAULT 'new',
  unsubscribed BOOLEAN DEFAULT FALSE,
  opens_count INT DEFAULT 0,
  last_opened TIMESTAMP,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS taskmind.outreach_messages (
  id SERIAL PRIMARY KEY,
  lead_id INT REFERENCES taskmind.outreach_leads(id) ON DELETE CASCADE,
  channel TEXT DEFAULT 'email',
  subject TEXT,
  body TEXT,
  status TEXT DEFAULT 'pending',
  error TEXT,
  sent_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS taskmind.outreach_logs (
  id SERIAL PRIMARY KEY,
  lead_id INT REFERENCES taskmind.outreach_leads(id) ON DELETE CASCADE,
  event TEXT,
  meta JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMP DEFAULT NOW()
);
"""

@app.on_event("startup")
def apply_bootstrap():
    """Create schema/tables if missing. Safe to run every boot."""
    try:
        with db_cursor() as cur:
            cur.execute(SCHEMA_SQL)
            cur.execute(TABLES_SQL)
        print("DB bootstrap complete.")
    except Exception as e:
        # Don't crash app; show in /dbcheck instead
        print("DB bootstrap error:", e)

# -----------------------------
# ROUTES
# -----------------------------

@app.get("/")
def home():
    return {
        "ok": True,
        "app": "TaskMind Tracker",
        "routes": ["/healthz", "/dbcheck", "/o/{lead_id}.png", "/u/{lead_id}"]
    }

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/dbcheck")
def dbcheck():
    """Verify DB connectivity and return a timestamp."""
    try:
        with db_cursor() as cur:
            cur.execute("SELECT NOW();")
            ts = cur.fetchone()[0]
        return {"db_connected": True, "timestamp": str(ts)}
    except Exception as e:
        return {"db_connected": False, "error": str(e)}

@app.get("/o/{lead_id}.png")
def open_tracker(lead_id: int):
    """
    Track open: increments opens_count and updates last_opened.
    Always returns a 1x1 transparent PNG so mail clients stay happy.
    """
    try:
        with db_cursor() as cur:
            cur.execute("""
                UPDATE taskmind.outreach_leads
                SET opens_count = COALESCE(opens_count, 0) + 1,
                    last_opened = NOW(),
                    updated_at = NOW()
                WHERE id = %s;
            """, (lead_id,))
    except Exception as e:
        print("open_tracker error:", e)

    # 1x1 transparent PNG
    pixel = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc``\x00"
        b"\x00\x00\x02\x00\x01E\x9c\xd5b\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    return Response(content=pixel, media_type="image/png")

@app.get("/u/{lead_id}")
def unsubscribe(lead_id: int):
    """Mark lead unsubscribed."""
    try:
        with db_cursor() as cur:
            cur.execute("""
                UPDATE taskmind.outreach_leads
                SET unsubscribed = TRUE,
                    status = 'unsubscribed',
                    updated_at = NOW()
                WHERE id = %s;
            """, (lead_id,))
        return {"ok": True, "message": "Unsubscribed successfully"}
    except Exception as e:
        print("unsubscribe error:", e)
        return {"ok": False, "error": str(e)}
