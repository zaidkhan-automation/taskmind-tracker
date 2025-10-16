# TaskMind Tracker (FastAPI)
Routes:
- GET /healthz            -> health
- GET /o/{lead_id}.png    -> open tracking pixel, updates last_opened, opens_count
- GET /u/{lead_id}        -> unsubscribe link, sets unsubscribed=true

ENV:
- DB_NAME, DB_USER, DB_PASS, DB_HOST, DB_PORT
- PORT (provided by Render)

Deploy:
1) Push this repo to GitHub.
2) Render: New Web Service -> connect repo -> Python -> build/start from render.yaml.
3) (Optional) Map CNAME track.taskmindai.net to the Render URL.
