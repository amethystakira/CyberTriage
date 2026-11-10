import { useState } from "react";
import "./App.css";

const navigation = [
  "Overview",
  "Investigations",
  "Evidence",
  "Analysis",
  "Findings",
  "Timeline",
  "Reports",
];

function App() {
  const [activePage, setActivePage] = useState("Overview");

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">CT</div>
          <div>
            <h2>CyberTriage</h2>
            <span>FORENSICS WORKBENCH</span>
          </div>
        </div>

        <nav className="nav-section">
          <span className="nav-heading">WORKSPACE</span>

          {navigation.map((item) => (
            <button
              key={item}
              className={`nav-item ${
                activePage === item ? "active" : ""
              }`}
              onClick={() => setActivePage(item)}
            >
              {item}
            </button>
          ))}
        </nav>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <span>Workspace / {activePage}</span>
        </header>

        <section className="content">
          <div className="eyebrow">INVESTIGATION CENTER</div>
          <h1>{activePage}</h1>
          <p>
            Manage your digital forensic investigations
            from one centralized workspace.
          </p>
        </section>
      </main>
    </div>
  );
}

export default App;