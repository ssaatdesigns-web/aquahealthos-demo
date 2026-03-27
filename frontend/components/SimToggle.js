import React, { useEffect, useState } from "react";
import { apiGet, apiPost } from "../lib/api";

export default function SimToggle({ pondId }) {
  const [running, setRunning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function refresh() {
    try {
      const data = await apiGet(`/api/v1/sim/status/${pondId}`);
      setRunning(Boolean(data.running));
    } catch (e) {
      setErr(e.message || ".");
    }
  }

  useEffect(() => {
    if (!pondId) return;

    refresh();
    const t = setInterval(refresh, 3000); // faster sync
    return () => clearInterval(t);
  }, [pondId]);

  async function toggle() {
    if (!pondId) return;

    setBusy(true);
    setErr("");

    try {
      if (running) {
        await apiPost(`/api/v1/sim/stop/${pondId}`);
      } else {
        await apiPost(`/api/v1/sim/start/${pondId}?interval_sec=2&incident_mode=true`);
      }

      // 🔥 HARD SYNC FROM BACKEND (THIS FIXES YOUR ISSUE)
      const data = await apiGet(`/api/v1/sim/status/${pondId}`);
      setRunning(Boolean(data.running));

    } catch (e) {
      setErr(e.message || "Toggle failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <button
        onClick={toggle}
        disabled={busy}
        className={`neo-btn ${running ? "neo-btn-on" : "neo-btn-off"}`}
      >
        {running ? "DEVICE ON" : "DEVICE OFF"}
      </button>

      {err && <div className="err">{err}</div>}
    </div>
  );
}
