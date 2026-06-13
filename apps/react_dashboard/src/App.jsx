import { useEffect, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE ?? "http://localhost:8000";

function MetricCard({ label, value }) {
  return (
    <div className="metric-card">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function App() {
  const [state, setState] = useState({ metrics: {}, events: [], alerts: [] });

  useEffect(() => {
    let stop = false;

    async function load() {
      const [metricsRes, eventsRes, alertsRes] = await Promise.all([
        fetch(`${API_BASE}/metrics/current`),
        fetch(`${API_BASE}/stream/recent`),
        fetch(`${API_BASE}/drift/events`),
      ]);
      const [metrics, events, alerts] = await Promise.all([
        metricsRes.json(),
        eventsRes.json(),
        alertsRes.json(),
      ]);
      if (!stop) {
        setState({ metrics, events, alerts });
      }
    }

    load();
    const timer = setInterval(load, 2500);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, []);

  return (
    <main className="shell">
      <section className="hero">
        <div>
          <p className="eyebrow">Recruiter Dashboard</p>
          <h1>Fraud signals as they happen.</h1>
          <p className="body">
            This React surface reads the same FastAPI service used by the Python demo UI.
          </p>
        </div>
        <div className="status">
          <span>Model version</span>
          <strong>{state.metrics.latest_model_version ?? "untrained"}</strong>
        </div>
      </section>

      <section className="metrics">
        <MetricCard label="Processed" value={state.metrics.processed_events ?? 0} />
        <MetricCard label="High Risk" value={state.metrics.high_risk_events ?? 0} />
        <MetricCard label="Drift Alerts" value={state.metrics.drift_alerts ?? 0} />
        <MetricCard label="PR-AUC" value={state.metrics.pr_auc ?? "-"} />
      </section>

      <section className="grid">
        <div className="panel">
          <h2>Recent Predictions</h2>
          {state.events.slice().reverse().map((event) => (
            <article key={event.transaction_id} className={`event-card ${event.risk_level.toLowerCase()}`}>
              <div className="row">
                <span className="tag">{event.risk_level}</span>
                <strong>{event.transaction_id}</strong>
              </div>
              <p>Probability {event.fraud_probability}</p>
              <p>Merchant {event.raw_transaction?.merchant_category} | Region {event.raw_transaction?.region}</p>
            </article>
          ))}
        </div>
        <div className="panel">
          <h2>Drift And Retraining</h2>
          {state.alerts.slice().reverse().map((alert, index) => (
            <article key={`${alert.feature_name}-${index}`} className="event-card">
              <div className="row">
                <span className="tag">{alert.feature_name}</span>
                <strong>{alert.direction} drift</strong>
              </div>
              <p>{alert.message}</p>
              <p>Score {alert.drift_score} vs threshold {alert.threshold}</p>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}

