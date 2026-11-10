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


function StatCard({ icon: Icon, label, value, color }) {
  return (
    <div className="stat-card">
      <div className="stat-top">
        <div className={`stat-icon ${color}`}>
          <Icon size={20} />
        </div>
      </div>

      <div className="stat-label">{label}</div>

      <div className="stat-bottom">
        <strong>{value}</strong>
      </div>
    </div>
  );
}


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
      <div className="sidebar-bottom">
          <div className="system-status">
            <span className="status-dot"></span>
            <div>
              <strong>API Online</strong>
              <span>Local backend</span>
            </div>
          </div>

          <div className="profile">
            <div className="profile-avatar">AP</div>
            <div>
              <strong>A. Pal</strong>
              <span>Local investigator</span>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
        <div className="topbar-left">
            <span>Workspace</span>
            <span className="breadcrumb-divider">/</span>
            <strong>{activePage}</strong>
        </div>

        <div className="topbar-right">
            <div className="environment-badge">
            <span className="status-dot"></span>
            Development Environment
            </div>
        </div>
        </header>

        <section className="content">
        <div className="page-heading">
            <div>
            <div className="eyebrow">INVESTIGATION CENTER</div>
            <h1>{activePage}</h1>
            <p>
                Manage your digital forensic investigations
                from one centralized workspace.
            </p>
            </div>
        </div>

        {activePage === "Overview" && (
            <section className="stats-grid">
            <StatCard
                icon={FolderSearch}
                label="Investigations"
                value="0"
                color="blue"
            />

            <StatCard
                icon={AlertTriangle}
                label="Findings"
                value="0"
                color="orange"
            />

            <StatCard
                icon={HardDrive}
                label="Evidence Items"
                value="0"
                color="purple"
            />

            <StatCard
                icon={LayoutDashboard}
                label="Completed Investigations"
                value="0"
                color="green"
            />
            </section>
        )}
        </section>
      </main>
    </div>
  );
}

export default App;