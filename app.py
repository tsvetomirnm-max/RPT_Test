from flask import Flask, Response, make_response
from datetime import datetime
import random
import html

app = Flask(__name__)

latest = None
latest_ts = None


def no_cache_html(html_text: str) -> Response:
    resp = make_response(html_text)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


@app.get("/")
def health():
    return Response("OK", mimetype="text/plain")


# Called by the iframe (same origin) after receiving a postMessage from SAC
@app.get("/trigger")
def trigger():
    global latest, latest_ts
    latest = random.randint(0, 999_999)
    latest_ts = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    return Response(f"Triggered. Current value: {latest}", mimetype="text/plain")


# Page embedded in SAC Web Page widget
@app.get("/result")
def result_page():
    value = "—" if latest is None else str(latest)
    ts = "—" if latest_ts is None else latest_ts

    # IMPORTANT: set this to your exact SAC tenant origin.
    # Example: "https://mytenant.eu10.sapanalytics.cloud"
    sac_origin = "https://<YOUR-SAC-TENANT-ORIGIN>"

    # Escape content for safe embedding in HTML
    value_js = html.escape(value)
    ts_js = html.escape(ts)

    html_page = f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8"/>
    <title>SAC Result</title>
    <meta name="viewport" content="width=device-width, initial-scale=1"/>
    <style>
      html, body {{
        height:100%;
      }}
      body {{
        font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
        display:flex; align-items:center; justify-content:center;
        margin:0;
      }}
      .card {{ text-align:center; }}
      .num {{ font-size: 12vw; line-height:1; font-weight: 700; }}
      .meta {{ margin-top: 0.5rem; color: #666; font-size: 0.9rem; }}
      .hint {{ margin-top: 1rem; font-size: 0.85rem; opacity: .6; }}
    </style>
  </head>
  <body>
    <div class="card">
      <div class="num" id="val">{value_js}</div>
      <div class="meta" id="ts">Updated: {ts_js}</div>
      <div class="hint">
        Iframe accepts postMessage "trigger" (or '{{"cmd":"trigger"}}') from SAC
        and posts back the currently displayed number to SAC.
      </div>
    </div>

    <script>
      // ========= helpers =========
      function getCmd(data) {{
        if (typeof data === "string") {{
          const trimmed = data.trim();
          if (trimmed === "trigger") return "trigger";
          try {{
            const obj = JSON.parse(trimmed);
            return obj && obj.cmd;
          }} catch(e) {{
            return null;
          }}
        }}
        return null;
      }}

      function postValueToSAC() {{
        // send the exact value currently displayed
        var val = document.getElementById("val").textContent.trim();
        var ts = document.getElementById("ts").textContent.replace(/^Updated:\\s*/,'').trim();
        // Keep payload a string as per SAC API; using JSON string literal
        var message = JSON.stringify({{ cmd: "value", value: val, updated: ts }});
        try {{
          // Post to SAC parent window
          window.parent.postMessage(message, "{sac_origin}");
        }} catch(e) {{
          console.error("postMessage to SAC failed", e);
        }}
      }}

      // ========= receive from SAC (host) =========
      window.addEventListener("message", async (event) => {{
        // Optional strict origin check:
        // if (event.origin !== "{sac_origin}") return;

        const cmd = getCmd(event.data);
        if (cmd !== "trigger" && cmd !== "request") return;

        if (cmd === "request") {{
          // SAC is asking for the current value without changing it
          postValueToSAC();
          return;
        }}

        // cmd === "trigger": kick calc, then reload and post new value
        try {{
          await fetch("/trigger", {{ method: "GET", cache: "no-store" }});
          // Reload this page to show the new value (cache-busted)
          const url = new URL(window.location.href);
          url.searchParams.set("cb", Date.now().toString());
          window.location.replace(url.toString());
        }} catch (err) {{
          console.error("Trigger failed", err);
        }}
      }});

      // ========= send to SAC on load =========
      // Always tell SAC what value we display right now (no change to existing flow)
      window.addEventListener("DOMContentLoaded", () => {{
        postValueToSAC();
      }});
    </script>
  </body>
</html>"""
    return no_cache_html(html_page)


# Optional plain integer endpoint (for quick checks)
@app.get("/result-plain")
def result_plain():
    return Response("" if latest is None else str(latest), mimetype="text/plain")


if __name__ == "__main__":
    # Local testing only; on Render use gunicorn:
    # gunicorn -b 0.0.0.0:$PORT app:app
    app.run(host="0.0.0.0", port=3000, debug=True)
