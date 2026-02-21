import { useEffect, useState } from "react";
import { API_BASE } from "../lib/api";

export default function Home() {
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    fetch(`${API_BASE}/alerts/1`)
      .then(res => res.json())
      .then(data => setAlerts(data));
  }, []);

  return (
    <div style={{ padding: 40 }}>
      <h1>AquaHealthOS Demo</h1>
      <h2>Alerts</h2>
      <ul>
        {alerts.map(alert => (
          <li key={alert.id}>
            {alert.message} - {alert.severity}
          </li>
        ))}
      </ul>
    </div>
  );
}
