import { ApiStatus } from "@/components/api-status";
import Link from "next/link";

const stages = [
  { number: "01", title: "Observe", detail: "Collect metrics, logs, and events from a controlled Mininet network." },
  { number: "02", title: "Diagnose", detail: "Correlate evidence, analyze topology, and rank probable causes." },
  { number: "03", title: "Explain", detail: "Present impact, evidence, and AI-assisted recommendations." },
];

export default function Home() {
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Application navigation">
        <Link className="brand" href="/" aria-label="NetRCA home">NET<span>RCA</span><small>NETWORK OPERATIONS</small></Link>
        <div className="sidebar-group">
          <p className="eyebrow">WORKSPACE</p>
          <span className="nav-active" aria-current="page"><span aria-hidden>◈</span> Overview</span>
        </div>
        <div className="sidebar-note"><span className="note-dot" /> FOUNDATION / PHASE 01</div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="crumb">NETRCA <span>/</span> OVERVIEW</div>
          <ApiStatus />
        </header>

        <section className="hero">
          <p className="eyebrow accent">AI-POWERED NETWORK INVESTIGATION</p>
          <h1>Clarity when the<br />{" "}<em>network fails.</em></h1>
          <p className="hero-description">NetRCA is being built to turn network symptoms into evidence-backed root cause analysis and practical next steps.</p>
          <div className="hero-foot"><span className="pill">PHASE 01</span><span>Application foundation</span></div>
        </section>

        <div className="content-grid">
          <section className="panel" aria-labelledby="pipeline-title">
            <div className="panel-heading"><p className="eyebrow">SYSTEM DESIGN</p><h2 id="pipeline-title">Investigation pipeline</h2></div>
            <div className="stage-list">
              {stages.map((stage) => <div className="stage" key={stage.number}><span className="stage-number">{stage.number}</span><div><h3>{stage.title}</h3><p>{stage.detail}</p></div><span className="stage-arrow" aria-hidden>↗</span></div>)}
            </div>
          </section>
          <section className="panel status-panel" aria-labelledby="readiness-title">
            <div className="panel-heading"><p className="eyebrow">CURRENT STATUS</p><h2 id="readiness-title">Ready for the next phase</h2></div>
            <p>The web shell and API health check are available. Network simulation, monitoring, incident analysis, and Gemini integration will be added in later phases.</p>
            <div className="readiness-line"><span>FOUNDATION</span><strong>IN PROGRESS</strong></div>
            <div className="readiness-line"><span>NETWORK DATA</span><strong>NOT CONNECTED</strong></div>
          </section>
        </div>
        <footer>NetRCA · Controlled simulation project · Phase 1</footer>
      </main>
    </div>
  );
}
