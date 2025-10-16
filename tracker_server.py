from fastapi import FastAPI, Request, Response
from datetime import datetime
import os, psycopg2

app = FastAPI()

def get_conn():
    return psycopg2.connect(
        dbname=os.getenv("DB_NAME", "taskmind_db"),
        user=os.getenv("DB_USER", "zaidkhan"),
        password=os.getenv("DB_PASS", "StrongPassword123"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )

PIXEL = (b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
         b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
         b'\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82')

@app.get("/healthz")
def health():
    return {"ok": True}

@app.get("/o/{lead_id}.png")
def track_open(lead_id: int, request: Request):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        UPDATE taskmind.outreach_leads
        SET last_opened = NOW(),
            opens_count = COALESCE(opens_count,0)+1,
            status='opened'
        WHERE id=%s;
    """, (lead_id,))
    conn.commit(); conn.close()
    return Response(content=PIXEL, media_type="image/png",
                    headers={"Cache-Control":"no-cache"})

@app.get("/u/{lead_id}")
def unsubscribe(lead_id: int):
    conn = get_conn(); cur = conn.cursor()
    cur.execute("""
        UPDATE taskmind.outreach_leads
        SET unsubscribed=TRUE, status='opted_out', updated_at=NOW()
        WHERE id=%s;
    """, (lead_id,))
    conn.commit(); conn.close()
    return Response(content="<h3>Unsubscribed ✅</h3>", media_type="text/html")
