from fastapi import FastAPI, Request, Response
from datetime import datetime
import os
import psycopg2

app = FastAPI()

# DB from env (so you can point to hosted Postgres later)
DB_NAME = os.getenv("DB_NAME", "taskmind_db")
DB_USER = os.getenv("DB_USER", "zaidkhan")
DB_PASS = os.getenv("DB_PASS", "StrongPassword123")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")

conn = psycopg2.connect(
    dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT
)
cur = conn.cursor()

PIXEL = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
         b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
         b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')

@app.get("/healthz")
def health():
    return {"ok": True}

@app.get("/o/{lead_id}.png")
def track_open(lead_id: int, request: Request):
    cur.execute("""
        UPDATE taskmind.outreach_leads
        SET last_opened = NOW(),
            opens_count = COALESCE(opens_count,0)+1,
            status='opened'
        WHERE id=%s;
    """, (lead_id,))
    conn.commit()
    return Response(content=PIXEL, media_type="image/png",
                    headers={"Cache-Control":"no-cache, no-store, must-revalidate"})

@app.get("/u/{lead_id}")
def unsubscribe(lead_id: int):
    cur.execute("""
        UPDATE taskmind.outreach_leads
        SET unsubscribed=TRUE, status='opted_out', updated_at=NOW()
        WHERE id=%s;
    """, (lead_id,))
    conn.commit()
    return Response(content="<h3>Unsubscribed ✅</h3>", media_type="text/html")
