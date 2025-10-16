from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
import psycopg2, os
from datetime import datetime

app = FastAPI()

# CORS – so it doesn’t block if accessed from your apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_conn():
    """Connects to Render PostgreSQL or local dev DB automatically"""
    try:
        url = os.getenv("DATABASE_URL")
        if url:
            # Render Postgres requires SSL
            return psycopg2.connect(url, sslmode="require")
        # fallback (local)
        return psycopg2.connect(
            dbname=os.getenv("DB_NAME", "taskmind_db"),
            user=os.getenv("DB_USER", "zaidkhan"),
            password=os.getenv("DB_PASS", "StrongPassword123"),
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432"),
        )
    except Exception as e:
        print("DB connection failed:", e)
        raise

@app.get("/")
def home():
    return {
        "status": "ok",
        "routes": ["/healthz", "/o/{lead_id}.png", "/u/{lead_id}"]
    }

@app.get("/healthz")
def health():
    return {"ok": True}

@app.get("/o/{lead_id}.png")
def open_tracker(lead_id: int):
    """Marks a lead as opened and returns a 1x1 transparent pixel"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            UPDATE taskmind.outreach_leads
            SET opens_count = COALESCE(opens_count, 0) + 1,
                last_opened = NOW()
            WHERE id = %s;
        """, (lead_id,))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print("Tracker update failed:", e)

    # 1x1 transparent PNG
    pixel = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc`\x00\x00\x00\x02\x00\x01E\x9c\xd5b\x00\x00\x00\x00IEND\xaeB\x82"
    return Response(content=pixel, media_type="image/png")

@app.get("/u/{lead_id}")
def unsubscribe(lead_id: int):
    """Marks a lead as unsubscribed"""
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            UPDATE taskmind.outreach_leads
            SET unsubscribed = TRUE, status = 'unsubscribed'
            WHERE id = %s;
        """, (lead_id,))
        conn.commit()
        cur.close()
        conn.close()
        return {"message": "Unsubscribed successfully."}
    except Exception as e:
        print("Unsubscribe failed:", e)
        return {"error": str(e)}
