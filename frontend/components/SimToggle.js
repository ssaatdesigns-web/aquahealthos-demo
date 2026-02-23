// frontend/components/SimToggle.js
import React, { useEffect, useState } from "react";
import { apiGet, apiPost, API_BASE } from "../lib/api";

export default function SimToggle({ pondId }) {
  const [running, setRunning] = useState(false);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function refresh() {
    try {
      const data = await apiGet(`/api/v1/sim/status/${pondId}`);
      setRunning(Boolean(data.running));
    } catch (e) {
      setErr(String(e));
    }
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, [pondId]);

  async function toggle() {
    setBusy(true);
    try {
      if (running) {
        await apiPost(`/api/v1/sim/stop/${pondId}`);
        setRunning(false);
      } else {
        await apiPost(`/api/v1/sim/start/${pondId}?interval_sec=5&incident_mode=true`);
        setRunning(true);
      }
    } catch (e) {
      setErr(String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <button
      onClick={toggle}
      disabled={busy}
      className={`neo-btn ${running ? "neo-btn-on" : "neo-btn-off"}`}
    >
      {running ? "DEVICE ON" : "DEVICE OFF"}
    </button>
  );
}
