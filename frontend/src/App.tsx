import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";

import { API_URL, apiGet, type DbHealth } from "./api";
import Analyze from "./pages/Analyze";
import History from "./pages/History";
import VerdictDetail from "./pages/VerdictDetail";

function ApiStatus() {
  const [state, setState] = useState<"checking" | "ok" | "down">("checking");

  useEffect(() => {
    apiGet<DbHealth>("/health/db")
      .then((data) => setState(data.database === "ok" ? "ok" : "down"))
      .catch(() => setState("down"));
  }, []);

  const label =
    state === "checking" ? "checking API…" : state === "ok" ? "API + DB ok" : "API unreachable";

  return (
    <div className="status">
      <span className={`dot ${state === "ok" ? "ok" : state === "down" ? "bad" : ""}`} />
      {label} <span style={{ opacity: 0.6 }}>· {API_URL}</span>
    </div>
  );
}

export default function App() {
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          <strong>Phish</strong>
          <span>blue team</span>
        </div>
        <NavLink to="/" end className="navitem">
          Analyze
        </NavLink>
        <NavLink to="/history" className="navitem">
          History
        </NavLink>
      </aside>

      <main className="main">
        <Routes>
          <Route path="/" element={<Analyze />} />
          <Route path="/history" element={<History />} />
          <Route path="/verdicts/:verdictId" element={<VerdictDetail />} />
        </Routes>
        <div style={{ marginTop: 24 }}>
          <ApiStatus />
        </div>
      </main>
    </div>
  );
}
