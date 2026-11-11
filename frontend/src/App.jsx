
import { useState, useEffect, useRef } from "react";

import {
  LayoutDashboard,
  FolderSearch,
  HardDrive,
  ScanSearch,
  AlertTriangle,
  Clock3,
  FileBarChart,
  Activity,
  Bell,
  Search,
  X,
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
        <span className="stat-change">Overview metric</span>
      </div>
    </div>
  );
}

function EmptyState({ icon: Icon, title, description }) {
  return (
    <div className="activity-empty">
      <div className="activity-empty-icon">
        <Icon size={22} />
      </div>

      <p>{title}</p>
      <span>{description}</span>
    </div>
  );
}

function App() {
  const [activePage, setActivePage] = useState("Overview");
  const [showNotifications, setShowNotifications] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const notificationRef = useRef(null);

  const currentHour = new Date().getHours();

  const greeting =
    currentHour < 12
      ? "Good morning"
      : currentHour < 18
      ? "Good afternoon"
      : "Good evening";

  // Handle notification outside clicks and Escape key
  useEffect(() => {
    function handleClickOutside(event) {
      if (
        notificationRef.current &&
        !notificationRef.current.contains(event.target)
      ) {
        setShowNotifications(false);
      }
    }

    function handleEscapeKey(event) {
      if (event.key === "Escape") {
        setShowNotifications(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("keydown", handleEscapeKey);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("keydown", handleEscapeKey);
    };
  }, []);

  // Handle Cmd + K / Ctrl + K search shortcut
  useEffect(() => {
    function handleSearchShortcut(event) {
      if (
        (event.metaKey || event.ctrlKey) &&
        event.key.toLowerCase() === "k"
      ) {
        event.preventDefault();
        document.querySelector(".header-search input")?.focus();
      }
    }

    document.addEventListener("keydown", handleSearchShortcut);

    return () => {
      document.removeEventListener("keydown", handleSearchShortcut);
    };
  }, []);

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

          {navigation
            .filter((item) =>
              item.label.toLowerCase().includes(searchQuery.toLowerCase())
            )
            .map((item) => (
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

          {navigation.filter((item) =>
            item.label.toLowerCase().includes(searchQuery.toLowerCase())
          ).length === 0 && (
            <p className="no-search-results">No sections found</p>
          )}
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
            <div className="header-search">
              <Search size={16} />

              <input
                type="text"
                placeholder="Search workspace..."
                aria-label="Search workspace"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
              />

              {searchQuery ? (
                <button
                  className="clear-search-button"
                  onClick={() => setSearchQuery("")}
                  aria-label="Clear search"
                >
                  <X size={14} />
                </button>
              ) : (
                <kbd>⌘ K</kbd>
              )}
            </div>

            <div className="current-date">
              {new Date().toLocaleDateString("en-IN", {
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
            </div>

            <div
              className="notification-wrapper"
              ref={notificationRef}
            >
              <button
                className="notification-button"
                aria-label="Notifications"
                aria-expanded={showNotifications}
                onClick={() =>
                  setShowNotifications(!showNotifications)
                }
              >
                <Bell size={18} />
                <span className="notification-dot"></span>
              </button>

              {showNotifications && (
                <div className="notification-panel">
                  <h3>Notifications</h3>
                  <p>You're all caught up!</p>
                  <span>
                    New investigation updates will appear here.
                  </span>
                </div>
              )}
            </div>

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
              <h1>{greeting}, Investigator</h1>
              <p>
                Here's an overview of your digital forensic
                investigations.
              </p>
            </div>

            {activePage === "Overview" && (
              <button className="primary-button">
                <span>+</span>
                New Investigation
              </button>
            )}
          </div>

          {activePage === "Overview" && (
            <>
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

              <div className="activity-section">
                <div className="section-heading">
                  <div>
                    <h2>Recent Activity</h2>
                    <p>
                      Latest updates across your investigations
                    </p>
                  </div>

                  <button className="text-button">
                    View all
                  </button>
                </div>

                <EmptyState
                  icon={Activity}
                  title="No recent activity"
                  description="Activity will appear here as investigations progress."
                />
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
