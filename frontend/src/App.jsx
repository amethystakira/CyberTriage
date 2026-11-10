import { useState } from "react";
import {
  LayoutDashboard,
  FolderSearch,
  HardDrive,
  ScanSearch,
  AlertTriangle,
  Clock3,
  FileBarChart,
} from "lucide-react";

import "./App.css";

const navigation = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Investigations", icon: FolderSearch },
  { label: "Evidence", icon: HardDrive },
  { label: "Analysis", icon: ScanSearch },
  { label: "Findings", icon: AlertTriangle },
  { label: "Timeline", icon: Clock3 },
  { label: "Reports", icon: FileBarChart },
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

        <div className="workspace">
            <div className="workspace-avatar">IU</div>
            <div>
                <strong>Investigation Unit</strong>
                <span>Local workspace</span>
            </div>
            </div>

            <nav className="nav-section">
          <span className="nav-heading">WORKSPACE</span>

          {navigation.map((item) => (
            <button
                key={item.label}
                className={`nav-item ${
                activePage === item.label ? "active" : ""
                }`}
                onClick={() => setActivePage(item.label)}
            >
                <item.icon size={18} />
                <span>{item.label}</span>
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