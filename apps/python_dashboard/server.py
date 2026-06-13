from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT = PROJECT_ROOT / "services" / "fraud_platform" / "src"
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from fraud_platform.config import AppConfig
from fraud_platform.storage.event_store import JsonLineStore, JsonStateStore


INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Fraud Detection Live Demo</title>
    <style>
      :root {
        --bg: #f4efe6;
        --panel: #fffaf2;
        --ink: #17202a;
        --accent: #d35400;
        --accent-soft: #fde3cf;
        --danger: #c0392b;
        --ok: #1e8449;
        --line: #eadfce;
      }
      body {
        margin: 0;
        font-family: "Avenir Next", "Segoe UI", sans-serif;
        background:
          radial-gradient(circle at top right, rgba(211, 84, 0, 0.12), transparent 30%),
          linear-gradient(180deg, #f8f4ec 0%, var(--bg) 100%);
        color: var(--ink);
      }
      .shell {
        max-width: 1320px;
        margin: 0 auto;
        padding: 24px;
      }
      .hero {
        display: grid;
        grid-template-columns: 1.4fr 1fr;
        gap: 20px;
        margin-bottom: 20px;
      }
      .hero-card, .panel {
        background: var(--panel);
        border: 1px solid var(--line);
        border-radius: 22px;
        box-shadow: 0 16px 40px rgba(23, 32, 42, 0.08);
      }
      .hero-card {
        padding: 28px;
      }
      h1 {
        margin: 0 0 8px;
        font-size: clamp(2rem, 5vw, 4rem);
        line-height: 0.95;
        letter-spacing: -0.05em;
      }
      .kicker {
        text-transform: uppercase;
        letter-spacing: 0.12em;
        font-size: 0.78rem;
        color: var(--accent);
        margin-bottom: 12px;
      }
      .subtle {
        color: #5d6d7e;
      }
      .stat-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 14px;
      }
      .stat {
        padding: 18px;
      }
      .stat strong {
        display: block;
        font-size: 2rem;
        margin-top: 10px;
      }
      .layout {
        display: grid;
        grid-template-columns: 1.2fr 1fr;
        gap: 20px;
      }
      .panel {
        padding: 18px;
      }
      .panel h2 {
        margin-top: 0;
      }
      .stack {
        display: grid;
        gap: 20px;
      }
      .list {
        display: grid;
        gap: 10px;
        max-height: 420px;
        overflow: auto;
      }
      .card {
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 14px;
        background: white;
      }
      .high { border-left: 6px solid var(--danger); }
      .medium { border-left: 6px solid var(--accent); }
      .low { border-left: 6px solid var(--ok); }
      .pill {
        display: inline-block;
        font-size: 0.78rem;
        padding: 5px 10px;
        border-radius: 999px;
        background: var(--accent-soft);
        color: var(--accent);
        margin-right: 8px;
      }
      code {
        background: #f4efe6;
        padding: 2px 6px;
        border-radius: 8px;
      }
      @media (max-width: 900px) {
        .hero, .layout, .stat-grid {
          grid-template-columns: 1fr;
        }
      }
    </style>
  </head>
  <body>
    <div class="shell">
      <section class="hero">
        <div class="hero-card">
          <div class="kicker">Recruiter Demo Surface</div>
          <h1>Real-Time Fraud Detection</h1>
          <p class="subtle">
            Live transaction scoring, drift alerts, retraining signals, and current model metrics from the local event-driven demo.
          </p>
          <p><code>make train</code> then <code>make stream-demo</code> in one terminal and <code>make demo-ui</code> in another.</p>
        </div>
        <div class="hero-card">
          <div class="kicker">Current Model</div>
          <div id="model-version" class="subtle">Waiting for metrics...</div>
          <p id="model-metrics" class="subtle"></p>
        </div>
      </section>

      <section class="stat-grid">
        <div class="panel stat"><span class="subtle">Processed Events</span><strong id="processed">0</strong></div>
        <div class="panel stat"><span class="subtle">High Risk Alerts</span><strong id="high-risk">0</strong></div>
        <div class="panel stat"><span class="subtle">Drift Alerts</span><strong id="drift">0</strong></div>
        <div class="panel stat"><span class="subtle">Last Retrain</span><strong id="retrain">Never</strong></div>
      </section>

      <section class="layout" style="margin-top: 20px;">
        <div class="panel">
          <h2>Recent Scored Transactions</h2>
          <div id="events" class="list"></div>
        </div>
        <div class="stack">
          <div class="panel">
            <h2>Drift Monitor</h2>
            <div id="alerts" class="list"></div>
          </div>
          <div class="panel">
            <h2>Live Demo Script</h2>
            <p class="subtle">Talk track:</p>
            <p class="subtle">1. Start with the architecture and dataset.</p>
            <p class="subtle">2. Kick off the stream and show real-time scoring.</p>
            <p class="subtle">3. Point out the drift spikes and automated retraining.</p>
            <p class="subtle">4. Close with Docker, AWS, Kafka, Spark, and React paths in the repo.</p>
          </div>
        </div>
      </section>
    </div>

    <script>
      async function refresh() {
        const response = await fetch('/api/state');
        const payload = await response.json();
        const metrics = payload.metrics || {};
        document.getElementById('processed').textContent = metrics.processed_events ?? 0;
        document.getElementById('high-risk').textContent = metrics.high_risk_events ?? 0;
        document.getElementById('drift').textContent = metrics.drift_alerts ?? 0;
        document.getElementById('retrain').textContent = metrics.last_retrained_at ? new Date(metrics.last_retrained_at).toLocaleTimeString() : 'Never';
        document.getElementById('model-version').textContent = `Model version: ${metrics.latest_model_version ?? 'untrained'}`;
        document.getElementById('model-metrics').textContent = `PR-AUC ${metrics.pr_auc ?? '-'} | F1 ${metrics.f1 ?? '-'} | Recall ${metrics.recall ?? '-'}`;

        const events = (payload.events || []).slice().reverse().map((event) => {
          const level = (event.risk_level || 'LOW').toLowerCase();
          return `
            <div class="card ${level}">
              <div><span class="pill">${event.risk_level}</span><strong>${event.transaction_id}</strong></div>
              <div class="subtle">Probability: ${event.fraud_probability} | Amount: ${event.raw_transaction?.Amount ?? event.raw_transaction?.amount ?? '-'}</div>
              <div class="subtle">Merchant: ${event.raw_transaction?.merchant_category ?? '-'} | Region: ${event.raw_transaction?.region ?? '-'}</div>
            </div>
          `;
        }).join('');
        document.getElementById('events').innerHTML = events || '<div class="card"><span class="subtle">No transactions yet.</span></div>';

        const alerts = (payload.alerts || []).slice().reverse().map((alert) => `
          <div class="card">
            <div><span class="pill">${alert.feature_name}</span><strong>${alert.direction} drift</strong></div>
            <div class="subtle">${alert.message}</div>
            <div class="subtle">Score ${alert.drift_score} vs threshold ${alert.threshold}</div>
          </div>
        `).join('');
        document.getElementById('alerts').innerHTML = alerts || '<div class="card"><span class="subtle">No drift alerts yet.</span></div>';
      }

      refresh();
      setInterval(refresh, 2000);
    </script>
  </body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    config = AppConfig()
    scored_store = JsonLineStore(config.scored_events_path)
    alert_store = JsonLineStore(config.alerts_path)
    metrics_store = JsonStateStore(config.metrics_path)

    def do_GET(self) -> None:  # noqa: N802
        route = urlparse(self.path).path
        if route == "/":
            self._respond_html(INDEX_HTML)
            return
        if route == "/api/state":
            payload = {
                "events": self.scored_store.read_recent(limit=20),
                "alerts": self.alert_store.read_recent(limit=20),
                "metrics": self.metrics_store.read(),
            }
            self._respond_json(payload)
            return
        self.send_error(404, "Not found")

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _respond_html(self, body: str) -> None:
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _respond_json(self, payload: dict) -> None:
        encoded = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    config = AppConfig()
    config.ensure_dirs()
    server = ThreadingHTTPServer(("0.0.0.0", config.dashboard_port), DashboardHandler)
    print(f"Dashboard available at http://localhost:{config.dashboard_port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
