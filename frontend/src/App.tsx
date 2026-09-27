import { useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";

import { API_URL, apiGet, type DbHealth } from "./api";
import Analyze from "./pages/Analyze";
import History from "./pages/History";
import VerdictDetail from "./pages/VerdictDetail";

/* Icons are drawn, one consistent stroke and weight — never a unicode glyph. */
function ShieldIcon() {
  return (
    <svg viewBox="0 0 24 24" className="navicon" aria-hidden="true">
      <path d="M12 3l7 3v5.5c0 4.3-2.9 8.2-7 9.5-4.1-1.3-7-5.2-7-9.5V6l7-3z" />
      <path d="M9 12l2.2 2.2L15.5 10" />
    </svg>
  );
}

function HistoryIcon() {
  return (
    <svg viewBox="0 0 24 24" className="navicon" aria-hidden="true">
      <path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1" />
      <path d="M3.5 5v4h4" />
      <path d="M12 7.5V12l3 1.8" />
    </svg>
  );
}

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
    <div className="status" role="status" aria-live="polite">
      <span
        className={`dot ${state === "ok" ? "ok" : state === "down" ? "bad" : ""}`}
        aria-hidden="true"
      />
      {label} <span style={{ opacity: 0.6 }}>· {API_URL}</span>
    </div>
  );
}

export default function App() {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand">
          <strong>Phish</strong>
          <span>blue team</span>
        </div>
        <div className="topbar-nav">
          <NavLink to="/" end className="navitem">
            <ShieldIcon />
            Analyze
          </NavLink>
          <NavLink to="/history" className="navitem">
            <HistoryIcon />
            History
          </NavLink>
        </div>
        <div className="topbar-end">
          <ApiStatus />
        </div>
      </header>

      <main className="main">
        <Routes>
          <Route path="/" element={<Analyze />} />
          <Route path="/history" element={<History />} />
          <Route path="/verdicts/:verdictId" element={<VerdictDetail />} />
        </Routes>
      </main>
    </div>
  );
}
