import React, { useEffect, useMemo, useState } from "react";
import SimToggle from "../components/SimToggle";
import { apiGet } from "../lib/api";

import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend
} from "chart.js";
import { Line } from "react-chartjs-2";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend);

const POLL_MS = Number(process.env.NEXT_PUBLIC_POLL_MS || 5000);

function fmt(n, d = 2) {
  if (n === null || n === undefined) return "-";
  const v = Number(n);
  if (Number.isNaN(v)) return "-";
  return v.toFixed(d);
}

function statusColor(score) {
  if (score >= 75) return "lime";
  if (score >= 50) return "orange";
  return "red";
}

export default function Dashboard() {
  const [ponds, setPonds] = useState([]);
  const [pondId, setPondId] = useState(null);

  const [latest, setLatest] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [forecast, setForecast] = useState(null);

  const [err, setErr] = useState("");

  async function loadPonds() {
    const p = await apiGet("/api/v1/ponds");
    setPonds(p);
    if (!pondId && p.length) setPondId(p[0].id);
  }

  async function loadAll(id) {
    if (!id) return;
    setErr("");
    try {
      const [l, a, f] = await Promise.all([
        apiGet(`/api/v1/ponds/${id}/latest`),
        apiGet(`/api/v1/ponds/${id}/alerts?limit=10`),
        apiGet(`/api/v1/ponds/${id}/forecast?hours=24&step_minutes=60`)
      ]);
      setLatest(l);
      setAlerts(a);
      setForecast(f);
    } catch (e) {
      setErr(String(e.message || e));
    }
  }

  useEffect(() => {
    loadPonds();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!pondId) return;
    loadAll(pondId);
    const t = setInterval(() => loadAll(pondId), POLL_MS);
    return () => clearInterval(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pondId]);

  const forecastPoints = forecast?.points || [];

  const forecastChartData = useMemo(() => {
    const labels = forecastPoints.map(p => new Date(p.t).toLocaleString([], { hour: "2-digit", minute: "2-digit" }));
    return {
      labels,
      datasets: [
        { label: "Pred Health Score", data: forecastPoints.map(p => p.health_score) },
        { label: "Pred DO (mg/L)", data: forecastPoints.map(p => p.dissolved_oxygen) },
        { label: "Pred Ammonia", data: forecastPoints.map(p => p.ammonia) }
      ]
    };
  }, [forecastPoints]);

  const forecastChartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: "top" } },
    scales: { y: { beginAtZero: true } }
  }), []);

  const summary = forecast?.summary;

  return (
    <div className="container">
      <div className="card">
        <h1 className="h1">
          AquaHealthOS Dashboard <span className="badge">Live Monitoring</span>
        </h1>
        <div className="muted">Dashboard alerts only • Polling: {POLL_MS}ms</div>

        <div style={{ marginTop: 12, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <label className="muted">Pond:</label>
          <select
            className="select"
            value={pondId || ""}
            onChange={(e) => setPondId(Number(e.target.value))}
          >
            {ponds.map(p => (
              <option key={p.id} value={p.id}>{p.name} ({p.species})</option>
            ))}
          </select>

          <div style={{ marginLeft: "auto" }}>
            <SimToggle pondId={pondId || 1} />
          </div>
        </div>

        {err ? <div className="err" style={{ marginTop: 10 }}>{err}</div> : null}
      </div>

      {/* KPIs */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="h1" style={{ fontSize: 18 }}>Live Health</div>

        {!latest ? (
          <div className="muted" style={{ marginTop: 8 }}>
            No readings yet. Start simulation.
          </div>
        ) : (
          <>
            <div className="kpi" style={{ marginTop: 12 }}>
              <div className="kpiBox">
                <div className="kpiTitle">Health Score</div>
                <div className="kpiValue" style={{ color: statusColor(latest.health_score) }}>
                  {fmt(latest.health_score, 1)}
                </div>
              </div>
              <div className="kpiBox">
                <div className="kpiTitle">DO (mg/L)</div>
                <div className="kpiValue">{fmt(latest.dissolved_oxygen, 2)}</div>
              </div>
              <div className="kpiBox">
                <div className="kpiTitle">Ammonia</div>
                <div className="kpiValue">{fmt(latest.ammonia, 3)}</div>
              </div>
            </div>

            <div className="kpi" style={{ marginTop: 12 }}>
              <div className="kpiBox">
                <div className="kpiTitle">Temperature (°C)</div>
                <div className="kpiValue">{fmt(latest.temperature, 1)}</div>
              </div>
              <div className="kpiBox">
                <div className="kpiTitle">pH</div>
                <div className="kpiValue">{fmt(latest.ph, 2)}</div>
              </div>
              <div className="kpiBox">
                <div className="kpiTitle">Turbidity</div>
                <div className="kpiValue">{fmt(latest.turbidity, 1)}</div>
              </div>
            </div>

            <div className="muted" style={{ marginTop: 10, fontSize: 12 }}>
              Last update: {new Date(latest.created_at).toLocaleString()}
            </div>
          </>
        )}
      </div>

      {/* Alerts */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="h1" style={{ fontSize: 18 }}>Recent Alerts</div>
        {alerts.length === 0 ? (
          <div className="muted" style={{ marginTop: 8 }}>No active alerts.</div>
        ) : (
          alerts.map(a => (
            <div key={a.id} className="alert">
              <div>
                <div><b>{String(a.severity).toUpperCase()}</b> — {a.message}</div>
                <div className="muted" style={{ fontSize: 12 }}>{new Date(a.created_at).toLocaleString()}</div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* AI Forecast */}
      <div className="card" style={{ marginTop: 16 }}>
        <div className="h1" style={{ fontSize: 18 }}>AI Prediction (Next 24 Hours)</div>
        <div className="muted">
          Baseline trend forecast using recent readings → predicted DO/ammonia → risk engine → health score.
        </div>

        {!forecastPoints.length ? (
          <div className="muted" style={{ marginTop: 10 }}>
            {forecast?.summary?.message || "Forecast unavailable. Start simulation and wait for a few readings."}
          </div>
        ) : (
          <>
            {/* Summary */}
            <div className="kpi" style={{ marginTop: 12 }}>
              <div className="kpiBox">
                <div className="kpiTitle">Predicted GOOD hours</div>
                <div className="kpiValue">{fmt(summary?.good_hours, 1)}</div>
              </div>
              <div className="kpiBox">
                <div className="kpiTitle">Predicted WATCH hours</div>
                <div className="kpiValue">{fmt(summary?.watch_hours, 1)}</div>
              </div>
              <div className="kpiBox">
                <div className="kpiTitle">Predicted CRITICAL hours</div>
                <div className="kpiValue">{fmt(summary?.critical_hours, 1)}</div>
              </div>
            </div>

            <div className="kpi" style={{ marginTop: 12 }}>
              <div className="kpiBox">
                <div className="kpiTitle">DO trend (mg/L per hour)</div>
                <div className="kpiValue">{fmt(summary?.do_slope_per_hour, 4)}</div>
              </div>
              <div className="kpiBox">
                <div className="kpiTitle">Ammonia trend (per hour)</div>
                <div className="kpiValue">{fmt(summary?.nh3_slope_per_hour, 5)}</div>
              </div>
              <div className="kpiBox">
                <div className="kpiTitle">Forecast step</div>
                <div className="kpiValue">{forecast?.step_minutes} min</div>
              </div>
            </div>

            {/* Chart */}
            <div style={{ height: 380, marginTop: 14 }}>
              <Line data={forecastChartData} options={forecastChartOptions} />
            </div>

            {/* Table */}
            <div style={{ marginTop: 14, overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid rgba(255,255,255,0.12)" }}>Time</th>
                    <th style={{ textAlign: "left", padding: 8, borderBottom: "1px solid rgba(255,255,255,0.12)" }}>Status</th>
                    <th style={{ textAlign: "right", padding: 8, borderBottom: "1px solid rgba(255,255,255,0.12)" }}>Health</th>
                    <th style={{ textAlign: "right", padding: 8, borderBottom: "1px solid rgba(255,255,255,0.12)" }}>DO</th>
                    <th style={{ textAlign: "right", padding: 8, borderBottom: "1px solid rgba(255,255,255,0.12)" }}>NH3</th>
                    <th style={{ textAlign: "right", padding: 8, borderBottom: "1px solid rgba(255,255,255,0.12)" }}>Temp</th>
                    <th style={{ textAlign: "right", padding: 8, borderBottom: "1px solid rgba(255,255,255,0.12)" }}>pH</th>
                  </tr>
                </thead>
                <tbody>
                  {forecastPoints.map((p, idx) => (
                    <tr key={idx}>
                      <td style={{ padding: 8, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                        {new Date(p.t).toLocaleString()}
                      </td>
                      <td style={{ padding: 8, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                        <span className="badge">{p.status}</span>
                      </td>
                      <td style={{ padding: 8, textAlign: "right", borderBottom: "1px solid rgba(255,255,255,0.06)", color: statusColor(p.health_score) }}>
                        {fmt(p.health_score, 2)}
                      </td>
                      <td style={{ padding: 8, textAlign: "right", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                        {fmt(p.dissolved_oxygen, 2)}
                      </td>
                      <td style={{ padding: 8, textAlign: "right", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                        {fmt(p.ammonia, 4)}
                      </td>
                      <td style={{ padding: 8, textAlign: "right", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                        {fmt(p.temperature, 1)}
                      </td>
                      <td style={{ padding: 8, textAlign: "right", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                        {fmt(p.ph, 2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="muted" style={{ marginTop: 10, fontSize: 12 }}>
              Generated at: {new Date(forecast.generated_at).toLocaleString()}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
