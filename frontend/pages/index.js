import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "../lib/api";
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
  return Number(n).toFixed(d);
}

function severityLabel(sev) {
  return sev === "HIGH" ? "HIGH" : sev === "MEDIUM" ? "MEDIUM" : "LOW";
}

export default function Home() {
  const [ponds, setPonds] = useState([]);
  const [pondId, setPondId] = useState(null);

  const [latest, setLatest] = useState(null);
  const [health, setHealth] = useState(null);
  const [alerts, setAlerts] = useState([]);
  const [series, setSeries] = useState([]);
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
      const [l, h, a, s] = await Promise.all([
        apiGet(`/api/v1/ponds/${id}/latest`),
        apiGet(`/api/v1/ponds/${id}/health`),
        apiGet(`/api/v1/ponds/${id}/alerts?include_resolved=false&limit=50`),
        apiGet(`/api/v1/ponds/${id}/timeseries?range_hours=24&limit=1000`)
      ]);
      setLatest(l);
      setHealth(h);
      setAlerts(a);
      setSeries(s.points || []);
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

  async function resolveAlert(id) {
    await apiPost(`/api/v1/alerts/${id}/resolve`);
    await loadAll(pondId);
  }

  const chartData = useMemo(() => {
    const labels = series.map(p => new Date(p.t).toLocaleTimeString());
    return {
      labels,
      datasets: [
        { label: "DO (mg/L)", data: series.map(p => p.dissolved_oxygen) },
        { label: "Ammonia", data: series.map(p => p.ammonia) },
        { label: "Health Score", data: series.map(p => p.health_score) }
      ]
    };
  }, [series]);

  const chartOptions = useMemo(() => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { position: "top" } },
    scales: {
      y: { beginAtZero: true }
    }
  }), []);

  const statusBadge = health?.status ? (
    <span className="badge">{health.status}</span>
  ) : null;

  return (
    <div className="container">
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="h1">AquaHealthOS Demo</div>
        <div className="muted">Live pond monitoring — dashboard alerts only</div>

        <div style={{ marginTop: 12, display: "flex", gap: 10, alignItems: "center" }}>
          <label className="muted">Pond:</label>
          <select
            className="select"
            value={pondId || ""}
            onChange={(e) => setPondId(Number(e.target.value))}
          >
            {ponds.map(p => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.species})
              </option>
            ))}
          </select>
          <span className="muted">Polling: {POLL_MS}ms</span>
        </div>

        {err ? <div style={{ marginTop: 12, color: "crimson" }}>{err}</div> : null}
      </div>

      <div className="row">
        <div className="card">
          <div style={{ display: "flex", alignItems: "center" }}>
            <div className="h1" style={{ fontSize: 18, marginBottom: 0 }}>Health</div>
            {statusBadge}
          </div>

          <div className="kpi" style={{ marginTop: 12 }}>
            <div className="kpiBox">
              <div className="kpiTitle">Health Score</div>
              <div className="kpiValue">{fmt(health?.health_score, 1)}</div>
            </div>
            <div className="kpiBox">
              <div className="kpiTitle">DO Risk</div>
              <div className="kpiValue">{fmt(health?.do_risk, 1)}</div>
            </div>
            <div className="kpiBox">
              <div className="kpiTitle">Ammonia Risk</div>
              <div className="kpiValue">{fmt(health?.nh3_risk, 1)}</div>
            </div>
          </div>

          <div style={{ marginTop: 14 }} className="muted">
            Latest reading:{" "}
            {latest ? new Date(latest.created_at).toLocaleString() : "-"}
          </div>

          <div className="kpi" style={{ marginTop: 12 }}>
            <div className="kpiBox">
              <div className="kpiTitle">DO (mg/L)</div>
              <div className="kpiValue">{fmt(latest?.dissolved_oxygen, 2)}</div>
            </div>
            <div className="kpiBox">
              <div className="kpiTitle">Ammonia</div>
              <div className="kpiValue">{fmt(latest?.ammonia, 3)}</div>
            </div>
            <div className="kpiBox">
              <div className="kpiTitle">Temp (°C)</div>
              <div className="kpiValue">{fmt(latest?.temperature, 1)}</div>
            </div>
          </div>

          <div className="kpi" style={{ marginTop: 12 }}>
            <div className="kpiBox">
              <div className="kpiTitle">pH</div>
              <div className="kpiValue">{fmt(latest?.ph, 2)}</div>
            </div>
            <div className="kpiBox">
              <div className="kpiTitle">Turbidity</div>
              <div className="kpiValue">{fmt(latest?.turbidity, 1)}</div>
            </div>
            <div className="kpiBox">
              <div className="kpiTitle">Reading ID</div>
              <div className="kpiValue">{latest?.id ?? "-"}</div>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="h1" style={{ fontSize: 18 }}>Alerts (Unresolved)</div>
          <div className="muted">Resolve alerts to clear them from the active list.</div>

          <div style={{ marginTop: 10 }}>
            {alerts.length === 0 ? (
              <div className="muted" style={{ marginTop: 10 }}>No active alerts</div>
            ) : (
              alerts.map(a => (
                <div key={a.id} className="alert">
                  <div>
                    <div><b>{severityLabel(a.severity)}</b> — {a.message}</div>
                    <div className="muted" style={{ fontSize: 12 }}>
                      {new Date(a.created_at).toLocaleString()}
                    </div>
                  </div>
                  <button className="btn" onClick={() => resolveAlert(a.id)}>
                    Resolve
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="h1" style={{ fontSize: 18 }}>Trends (Last 24h)</div>
        <div className="muted">DO, Ammonia, and Health Score time series.</div>

        <div style={{ height: 380, marginTop: 12 }}>
          <Line data={chartData} options={chartOptions} />
        </div>
      </div>
    </div>
  );
}
