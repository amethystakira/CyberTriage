
import { useState, useEffect, useRef, useCallback } from "react";

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
  RefreshCw,
} from "lucide-react";

import "./App.css";

const emptyWorkspace = {
  investigations: [],
  evidence: [],
  findings: [],
  timeline: [],
  analysis_runs: [],
};

const defaultSettings = {
  workspaceName: "Investigation Unit",
  investigatorName: "A. Pal",
  defaultSeverity: "Unassigned",
};

function readSettings() {
  try {
    return {
      ...defaultSettings,
      ...JSON.parse(
        localStorage.getItem("cybertriage-settings") || "{}"
      ),
    };
  } catch {
    return defaultSettings;
  }
}

const navigation = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Investigations", icon: FolderSearch },
  { label: "Evidence", icon: HardDrive },
  { label: "Analysis", icon: ScanSearch },
  { label: "Findings", icon: AlertTriangle },
  { label: "Timeline", icon: Clock3 },
  { label: "Reports", icon: FileBarChart },
];

const pageDescriptions = {
  Overview: "Here's an overview of your digital forensic investigations.",
  Investigations: "Create and manage your digital forensic investigations.",
  Evidence: "Organize and examine collected digital evidence.",
  Analysis: "Analyze evidence to identify suspicious patterns.",
  Findings: "Review important findings from your investigations.",
  Timeline: "Track important events across your investigations.",
  Reports: "Generate and manage investigation reports.",
};

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

async function apiRequest(url, options = {}) {
  const response = await fetch(url, options);

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    throw new Error(
      data.detail || data.message || "Something went wrong."
    );
  }

  return data;
}

function App() {
  const [activePage, setActivePage] = useState("Overview");
  const [workspace, setWorkspace] = useState(emptyWorkspace);
  const [settings, setSettings] = useState(readSettings);
  const [apiStatus, setApiStatus] = useState("Checking");
  const [showNotifications, setShowNotifications] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [caseError, setCaseError] = useState("");
  const [lastRefreshed, setLastRefreshed] = useState(new Date());
  const [unreadCount, setUnreadCount] = useState(2);

  const loadWorkspace = useCallback(async () => {
  const response = await fetch("/api/reports");

  if (!response.ok) {
    throw new Error("Could not load workspace data from the API.");
  }

  const data = await response.json();

  setWorkspace({ ...emptyWorkspace, ...data });
}, []);

useEffect(() => {
  let isCurrent = true;

  const checkApi = () => {
    fetch("/api/health")
      .then((response) => {
        if (!response.ok) {
          throw new Error("API unavailable");
        }

        return response.json();
      })
      .then(() => {
        if (isCurrent) {
          setApiStatus("Online");
        }
      })
      .catch(() => {
        if (isCurrent) {
          setApiStatus("Offline");
        }
      });
  };

  checkApi();

  const timer = window.setInterval(checkApi, 30000);

  return () => {
    isCurrent = false;
    window.clearInterval(timer);
  };
}, []);

  const notificationRef = useRef(null);
  const refreshTimerRef = useRef(null);

  const currentHour = new Date().getHours();

  const greeting =
    currentHour < 12
      ? "Good morning"
      : currentHour < 18
      ? "Good afternoon"
      : "Good evening";

    

  const activeNavigation = navigation.find(
    (item) => item.label === activePage
  );

  const ActiveIcon = activeNavigation?.icon || LayoutDashboard;

  const filteredNavigation = navigation.filter((item) =>
    item.label.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Close notifications on outside click or Escape
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

  // Focus search using Cmd + K or Ctrl + K
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

  // Clear any pending refresh timer when unmounting
  useEffect(() => {
    return () => {
      if (refreshTimerRef.current !== null) {
        clearTimeout(refreshTimerRef.current);
      }
    };
  }, []);

    function handleRefresh() {
        if (isLoading) return;

        setIsLoading(true);

        refreshTimerRef.current = setTimeout(() => {
            setIsLoading(false);
            setLastRefreshed(new Date());
            refreshTimerRef.current = null;
        }, 1200);
    }

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
            <strong>{settings.workspaceName}</strong>
            <span>Local workspace</span>
          </div>
        </div>

        <nav className="nav-section">
          <span className="nav-heading">WORKSPACE</span>

          {filteredNavigation.map((item) => (
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

          {filteredNavigation.length === 0 && (
            <p className="no-search-results">No sections found</p>
          )}
        </nav>

        <div className="system-status">
            <span className={`status-dot ${apiStatus.toLowerCase()}`} />
            <div>
                <strong>API {apiStatus.toLowerCase()}</strong>
                <span>Local backend</span>
            </div>
        </div>

          <div className="profile">
            <div className="profile-avatar">AP</div>
            <div>
              <strong>{settings.investigatorName}</strong>
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
                  type="button"
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
                type="button"
                className="notification-button"
                title="View notifications"
                aria-label="Notifications"
                aria-expanded={showNotifications}
                onClick={() => {
                    setShowNotifications((previous) => !previous);
                    setUnreadCount(0);
                }}
              >
                <Bell size={18} />
                {unreadCount > 0 && (
                    <span className="notification-count">{unreadCount}</span>
                )}
              </button>

              
            {showNotifications && (
            <div className="notification-panel">
                <div className="notification-panel-header">
                <h3>Notifications</h3>
                <button
                    type="button"
                    className="close-notifications"
                    onClick={() => setShowNotifications((previous) => !previous)}
                    aria-label="Close notifications"
                >
                    <X size={15} />
                </button>
                </div>

                <button
                type="button"
                className="mark-read-button"
                onClick={() => setUnreadCount(0)}
                >
                Mark all as read
                </button>

                {unreadCount > 0 ? (
                <>
                    <div className="notification-item">
                    <span className="notification-item-dot"></span>
                    <div>
                        <strong>New investigation created</strong>
                        <p>A new investigation is ready to be configured.</p>
                        <small>Just now</small>
                    </div>
                    </div>

                    <div className="notification-item">
                    <span className="notification-item-dot"></span>
                    <div>
                        <strong>Evidence storage updated</strong>
                        <p>Your evidence workspace is ready.</p>
                        <small>5 minutes ago</small>
                    </div>
                    </div>
                </>
                ) : (
                <div className="notification-empty">
                    <Bell size={20} />
                    <p>You're all caught up!</p>
                    <span>No unread notifications.</span>
                </div>
                )}
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
          {isLoading && (
            <div
              className="loading-indicator"
              role="status"
              aria-live="polite"
            >
              <div className="loading-spinner"></div>
              <span>Loading workspace...</span>
            </div>
          )}

          <div className="page-heading">
            <div className="page-title-group">
              <div className="page-title-icon">
                <ActiveIcon size={22} />
              </div>

              <div>
                <div className="eyebrow">
                  INVESTIGATION CENTER
                </div>

                <h1>
                  {activePage === "Overview"
                    ? `${greeting}, Investigator`
                    : activePage}
                </h1>

                <p>{pageDescriptions[activePage]}</p>
              </div>
            </div>

            {activePage === "Overview" && (
              <div className="heading-actions">
                <button
                    className="secondary-button"
                    onClick={handleRefresh}
                    disabled={isLoading}
                    >
                    <RefreshCw size={14} className={isLoading ? "spin" : ""} />
                    {isLoading ? "Refreshing..." : "Refresh"}
                </button>

            <span className="last-refreshed">
                Updated at {lastRefreshed.toLocaleTimeString("en-IN", {
                    hour: "2-digit",
                    minute: "2-digit",
                })}
            </span>

                <button
                  type="button"
                  className="primary-button"
                >
                  <span>+</span>
                  New Investigation
                </button>
              </div>
            )}
          </div>

          {activePage === "Overview" && (
            <>
              <section className="stats-grid">
                <StatCard
                  icon={FolderSearch}
                  label="Investigations"
                  value={workspace.investigations.length}
                  color="blue"
                />

                <StatCard
                  icon={AlertTriangle}
                  label="Findings"
                  value={workspace.findings.length}
                  color="orange"
                />

                <StatCard
                  icon={HardDrive}
                  label="Evidence Items"
                  value={workspace.evidence.length}
                  color="purple"
                />

                <StatCard
                  icon={LayoutDashboard}
                  label="Completed Investigations"
                  value={workspace.investigations.filter((item) => item.status === "Completed").length}
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

                  <button
                    type="button"
                    className="text-button"
                  >
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
