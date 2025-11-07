from flask import Flask, Response
from datetime import datetime
import random

app = Flask(__name__)

latest = None
latest_ts = None

@app.get("/")
def health():
    return Response("OK", mimetype="text/plain")

# Will be called via URL open from SAC (GET only)
@app.get("/trigger")
def trigger():
    global latest, latest_ts
    latest = random.randint(0, 999999)
    latest_ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    return Response(f"Triggered. Current value: {latest}", mimetype="text/plain")

# Simple HTML page to embed in SAC Web Page widget
@app.get("/result")
def result_page():
    value = "—" if latest is None else str(latest)
    ts = "—" if latest_ts is None else latest_ts
    html = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <title>SAC Result</title>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <style>
      body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
              display:flex; align-items:center; justify-content:center; height:100vh; margin:0; }}
      .card {{ text-align:center; }}
      .num {{ font-size: 12vw; line-height:1; font-weight: 700; }}
      .meta {{ margin-top: 0.5rem; color: #666; font-size: 0.9rem; }}
    </style>
  </head>
  <body>
    <div class="card">
      <div class="num">{value}</div>
      <div class="meta">Updated: {ts}</div>
    </div>
  </body>
</html>"""
    return Response(html, mimetype="text/html")

# Optional plain integer endpoint (useful for quick checks)
@app.get("/result-plain")
def result_plain():
    return Response("" if latest is None else str(latest), mimetype="text/plain")

if __name__ == "__main__":
    # For local testing only; Render will use gunicorn (see start command below)
    app.run(host="0.0.0.0", port=3000, debug=True)
