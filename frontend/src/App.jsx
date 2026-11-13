
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
  Settings,
  CheckCircle2,
  Upload,
  Download,
  ShieldCheck,
  Plus,
  ChevronDown,
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
  Settings: "Manage your workspace identity and investigation defaults.",
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

function ResourceEmptyState({ text }) {
  return <div className="resource-empty">{text}</div>;
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
  const [statusFilter, setStatusFilter] = useState("All cases");
  const [caseSearch, setCaseSearch] = useState("");
  const [apiStatus, setApiStatus] = useState("Checking");
  const [showNotifications, setShowNotifications] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [caseError, setCaseError] = useState("");
  const [workspaceError, setWorkspaceError] = useState("");
  const [lastRefreshed, setLastRefreshed] = useState(new Date());
  const [unreadCount, setUnreadCount] = useState(2);
  const [caseModalOpen, setCaseModalOpen] = useState(false);
  const [caseName, setCaseName] = useState("");
  const [isSaving, setIsSaving] = useState(false);

  const loadWorkspace = useCallback(async () => {
    setIsLoading(true);

    try {
      const response = await fetch("/api/reports");

      if (!response.ok) {
        throw new Error("Could not load workspace data from the API.");
      }

      const data = await response.json();
      setWorkspace({ ...emptyWorkspace, ...data });
      setLastRefreshed(new Date());
      setWorkspaceError("");
      return data;
    } catch (error) {
      setWorkspaceError(error.message);
      throw error;
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWorkspace().catch(() => {
      // The error is shown in the workspace interface.
    });
  }, [loadWorkspace]);

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

  const cases = workspace.investigations.map((item) => ({
  ...item,
  id: item.case_id,
}));

const filteredCases = cases.filter((item) => {
  const matchesSearch = `${item.id} ${item.name} ${item.status}`
    .toLowerCase()
    .includes(caseSearch.toLowerCase());

  const matchesStatus =
    statusFilter === "All cases" || item.status === statusFilter;

  return matchesSearch && matchesStatus;
});

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

  async function handleRefresh() {
    if (isLoading) return;

    try {
      await loadWorkspace();
    } catch {
      // loadWorkspace records the error for display.
    }
  }

  async function createCase(event) {
    event.preventDefault();
    setCaseError("");

    const trimmedCaseName = caseName.trim();
    if (!trimmedCaseName) {
      setCaseError("Investigation name cannot be empty.");
      return;
    }

    setIsSaving(true);

    try {
      await apiRequest("/api/cases", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: trimmedCaseName,
          investigator: settings.investigatorName,
          severity: settings.defaultSeverity,
        }),
      });

      await loadWorkspace();
      setCaseName("");
      setCaseModalOpen(false);
      setActivePage("Investigations");
    } catch (error) {
      setCaseError(error.message);
    } finally {
      setIsSaving(false);
    }
  }

    function openCaseForm() {
    setCaseName("");
    setCaseError("");
    setCaseModalOpen(true);
    }

  function saveSettings(nextSettings) {
    localStorage.setItem(
      "cybertriage-settings",
      JSON.stringify(nextSettings)
    );
    setSettings(nextSettings);
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
        <div className="nav-section settings-section">
            <span className="nav-heading">PREFERENCES</span>
            <button
                className={`nav-item ${
                activePage === "Settings" ? "active" : ""
                }`}
                onClick={() => setActivePage("Settings")}
            >
                <Settings size={18} />
                <span>Settings</span>
            </button>
        </div>

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

          {workspaceError && (
            <p className="form-error" role="alert">
              {workspaceError}
            </p>
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
                  onClick={openCaseForm}
                >
                  <span>+</span>
                  New Investigation
                </button>
              </div>
            )}
          </div>

          {activePage === "Overview" ? (
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
          ) : activePage === "Investigations" ? (
  <section className="activity-section">
    <div className="section-heading">
      <div>
        <h2>Investigations</h2>
        <p>Manage and review your investigation cases.</p>
      </div>
    </div>

    <div className="investigation-toolbar">
      <input
        type="search"
        placeholder="Search investigations..."
        value={caseSearch}
        onChange={(event) => setCaseSearch(event.target.value)}
      />

      <select
        value={statusFilter}
        onChange={(event) => setStatusFilter(event.target.value)}
      >
        <option>All cases</option>
        <option>Pending</option>
        <option>Analyzing</option>
        <option>Completed</option>
      </select>
    </div>

    {isLoading ? (
      <p>Loading investigations...</p>
    ) : filteredCases.length === 0 ? (
      <p>No matching investigations found.</p>
    ) : (
      <div className="investigation-table-wrapper">
        <table className="investigation-table">
          <thead>
            <tr>
              <th>Case ID</th>
              <th>Investigation</th>
              <th>Investigator</th>
              <th>Date Created</th>
              <th>Severity</th>
              <th>Status</th>
            </tr>
          </thead>

          <tbody>
            {filteredCases.map((item) => (
              <tr key={item.id}>
                <td>{item.id}</td>
                <td>{item.name}</td>
                <td>{item.investigator}</td>
                <td>{item.date}</td>
                <td>{item.severity}</td>
                <td>{item.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )}
  </section>
) : activePage === "Evidence" ? (
  <EvidenceModule
    cases={cases}
    evidence={workspace.evidence}
    onChanged={loadWorkspace}
  />
 ) : activePage === "Analysis" ? (
  <AnalysisModule
    evidence={workspace.evidence}
    runs={workspace.analysis_runs}
    onChanged={loadWorkspace}
  />
) : activePage === "Findings" ? (
  <FindingsModule
    cases={cases}
    findings={workspace.findings}
    onChanged={loadWorkspace}
  />
) : activePage === "Timeline" ? (
  <TimelineModule cases={cases} events={workspace.timeline} />
) : activePage === "Settings" ? (
  <SettingsModule settings={settings} onSave={saveSettings} />
) : null}
        </section>
      </main>

      {caseModalOpen && (
        <div
          className="modal-backdrop"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget && !isSaving) {
                setCaseModalOpen(false);
            }
          }}
        >
          <form className="case-dialog" onSubmit={createCase}>
            <div className="panel-heading">
              <div>
                <h3>New Investigation</h3>
                <p>Create a case in your local investigation database.</p>
              </div>

              <button
                type="button"
                className="icon-button"
                aria-label="Close"
                disabled={isSaving}
                onClick={() => setCaseModalOpen(false)}
              >
                <X size={19} />
              </button>
            </div>

            <label className="case-form-label" htmlFor="case-name">
              Investigation name
            </label>

            <input
              id="case-name"
              className="case-form-input"
              autoFocus
              required
              maxLength={200}
              value={caseName}
              onChange={(event) => {
                setCaseName(event.target.value);
                if (caseError) setCaseError("");
                }}
              placeholder="e.g. Suspicious login activity"
            />

            {caseError && (
              <p className="form-error" role="alert">
                {caseError}
              </p>
            )}

            <button
                type="button"
                className="secondary-button"
                disabled={isSaving}
                onClick={() => setCaseModalOpen(false)}
                >
                Cancel
            </button>

              <button
                type="submit"
                className="primary-button"
                disabled={isSaving}
              >
                {isSaving ? "Creating…" : "Create Investigation"}
              </button>
          </form>
        </div>
      )}
    </div>
  );
}


function ModuleHeading({ eyebrow, title, description, children }) {
  return (
    <section className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children}
    </section>
  );
}

function SettingsModule({ settings, onSave }) {
  const [form, setForm] = useState(settings);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
    setMessage("");
    setError("");
  }

  function submit(event) {
    event.preventDefault();
    try {
      onSave({
        workspaceName: form.workspaceName.trim(),
        investigatorName: form.investigatorName.trim(),
        defaultSeverity: form.defaultSeverity,
      });
      setMessage("Settings saved in this browser.");
    } catch (saveError) {
      setError(`Could not save settings: ${saveError.message}`);
    }
  }

  return <>
    <ModuleHeading
      eyebrow="PREFERENCES"
      title="Settings"
      description="Set the local workspace identity and defaults used for new investigations."
    />
    <form className="settings-form" onSubmit={submit}>
      <section className="panel settings-card">
        <div className="settings-card-heading">
          <div className="settings-card-icon">
            <Settings size={18} />
          </div>
          <div>
            <h2>Workspace identity</h2>
            <p>These details personalize the dashboard on this browser.</p>
          </div>
        </div>
        <label className="form-field">
          <span>Workspace name</span>
          <input
            required
            maxLength="60"
            value={form.workspaceName}
            onChange={(event) =>
              updateField("workspaceName", event.target.value)
            }
            placeholder="e.g. Incident Response Lab"
          />
        </label>
        <label className="form-field">
          <span>Investigator name</span>
          <input
            required
            maxLength="60"
            value={form.investigatorName}
            onChange={(event) =>
              updateField("investigatorName", event.target.value)
            }
            placeholder="Your name"
          />
        </label>
      </section>

      <section className="panel settings-card">
        <div className="settings-card-heading">
          <div className="settings-card-icon purple">
            <FolderSearch size={18} />
          </div>
          <div>
            <h2>New investigation defaults</h2>
            <p>
              New cases use these values. You can change their status later
              from the case menu.
            </p>
          </div>
        </div>
        <label className="form-field">
          <span>Default severity</span>
          <select
            value={form.defaultSeverity}
            onChange={(event) =>
              updateField("defaultSeverity", event.target.value)
            }
          >
            <option>Unassigned</option>
            <option>Low</option>
            <option>Medium</option>
            <option>High</option>
            <option>Critical</option>
          </select>
        </label>
      </section>

      <section className="panel settings-storage">
        <HardDrive size={18} />
        <div>
          <strong>Local data storage</strong>
          <p>
            Investigation records are stored in SQLite. Evidence files are
            kept in the project evidence folder. Workspace preferences are
            saved in this browser.
          </p>
        </div>
      </section>

      {error && <p className="form-error" role="alert">{error}</p>}
      {message && <p className="form-success" role="status">{message}</p>}

      <div className="settings-actions">
        <button
          type="button"
          className="secondary-button"
          onClick={() => {
            setForm(defaultSettings);
            setMessage("");
            setError("");
          }}
        >
          Restore defaults
        </button>
        <button className="primary-button">
          <CheckCircle2 size={16} /> Save Settings
        </button>
      </div>
    </form>
  </>;
}


function FindingsModule({ cases, findings, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function addFinding(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setBusy(true);
    setError("");
    setMessage("");

    const form = new FormData(formElement);
    const payload = Object.fromEntries(form.entries());
    payload.title = payload.title.trim();
    payload.description = payload.description.trim();
    if (!payload.case_id) payload.case_id = null;

    if (!payload.title || !payload.description) {
      setError("Enter both a finding title and description.");
      setBusy(false);
      return;
    }

    try {
      await apiRequest("/api/findings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      formElement.reset();
      setMessage("Finding recorded successfully.");
      await onChanged();
    } catch (createError) {
      setError(createError.message);
    } finally {
      setBusy(false);
    }
  }

  async function toggleFinding(item) {
    setError("");
    setMessage("");

    try {
      await apiRequest(
        `/api/findings/${encodeURIComponent(item.finding_id)}`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            status: item.status === "Open" ? "Resolved" : "Open",
          }),
        }
      );
      await onChanged();
    } catch (updateError) {
      setError(updateError.message);
    }
  }

  return (
    <>
      <ModuleHeading
        eyebrow="MANUAL REVIEW"
        title="Findings"
        description="Record observations, attach them to an investigation, and track whether they are resolved."
      />

      <form className="panel module-form finding-form" onSubmit={addFinding}>
        <label className="form-field">
          <span>Finding title</span>
          <input
            name="title"
            required
            maxLength={200}
            placeholder="e.g. Unknown remote connection"
          />
        </label>

        <label className="form-field">
          <span>Description</span>
          <textarea
            name="description"
            required
            rows={3}
            placeholder="What did you observe, and where?"
          />
        </label>

        <div className="form-row">
          <label className="form-field">
            <span>Investigation</span>
            <select name="case_id" defaultValue="">
              <option value="">Unlinked</option>
              {cases.map((item) => (
                <option key={item.case_id} value={item.case_id}>
                  {item.case_id} — {item.name}
                </option>
              ))}
            </select>
          </label>

          <label className="form-field">
            <span>Severity</span>
            <select name="severity" defaultValue="Medium">
              <option>Low</option>
              <option>Medium</option>
              <option>High</option>
              <option>Critical</option>
            </select>
          </label>

          <button className="primary-button" disabled={busy}>
            <Plus size={16} />
            {busy ? "Saving…" : "Add Finding"}
          </button>
        </div>

        {error && <p className="form-error" role="alert">{error}</p>}
        {message && <p className="form-success" role="status">{message}</p>}
      </form>

      <section className="panel resource-panel">
        <div className="panel-heading">
          <div>
            <h3>Recorded findings</h3>
            <p>{findings.length} finding(s)</p>
          </div>
        </div>

        {findings.length ? (
          <div className="resource-list">
            {findings.map((item) => (
              <article className="finding-row" key={item.finding_id}>
                <div className={`severity-mark ${(item.severity || "medium").toLowerCase()}`}>
                  <AlertTriangle size={17} />
                </div>

                <div className="resource-main">
                  <strong>{item.title}</strong>
                  <p>{item.description}</p>
                  <span>
                    {item.case_id || "Unlinked"}
                    {item.case_name ? ` · ${item.case_name}` : ""}
                    {item.created_at ? ` · ${formatDate(item.created_at)}` : ""}
                  </span>
                </div>

                <span className={`data-tag ${item.status === "Resolved" ? "resolved" : ""}`}>
                  {item.status}
                </span>

                <button
                  type="button"
                  className="secondary-button compact-button"
                  onClick={() => toggleFinding(item)}
                  disabled={busy}
                >
                  {item.status === "Open" ? "Resolve" : "Reopen"}
                </button>
              </article>
            ))}
          </div>
        ) : (
          <ResourceEmptyState text="No findings recorded. Add one above or run a rule scan on evidence." />
        )}
      </section>
    </>
  );
}


function TimelineModule({ cases, events }) {
  const [selectedCaseId, setSelectedCaseId] = useState("all");

  const visibleEvents = selectedCaseId === "all"
    ? events
    : events.filter((event) => event.case_id === selectedCaseId);

  const selectedCase = cases.find(
    (item) => item.case_id === selectedCaseId
  );

  return (
    <>
      <ModuleHeading
        eyebrow="CASE HISTORY"
        title="Timeline"
        description="Choose an investigation to view only its evidence, scans, findings, and status changes."
      >
        <label className="timeline-case-picker">
          <span>Timeline for</span>
          <span className="timeline-case-select-wrap">
            <select
              className="timeline-case-filter"
              aria-label="Choose case timeline"
              value={selectedCaseId}
              onChange={(event) => setSelectedCaseId(event.target.value)}
            >
              <option value="all">All investigations</option>
              {cases.map((item) => (
                <option key={item.case_id} value={item.case_id}>
                  {item.case_id} · {item.name}
                </option>
              ))}
            </select>
            <ChevronDown size={16} aria-hidden="true" />
          </span>
        </label>
      </ModuleHeading>

      <section className="panel timeline-panel">
        <div className="panel-heading timeline-heading">
          <div>
            <h3>
              {selectedCase
                ? `${selectedCase.case_id} · ${selectedCase.name}`
                : "Workspace activity"}
            </h3>
            <p>{visibleEvents.length} event(s) in this timeline</p>
          </div>
        </div>

        {visibleEvents.length ? (
          <ol className="timeline-list">
            {visibleEvents.map((event) => (
              <li key={event.event_id}>
                <span className="timeline-dot" />
                <div>
                  <strong>{event.event_type}</strong>
                  <p>{event.description}</p>
                  <span>
                    {event.case_id
                      ? `${event.case_id}${event.case_name ? ` · ${event.case_name}` : ""} · `
                      : "Workspace · "}
                    {formatDate(event.occurred_at)}
                  </span>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <ResourceEmptyState
            text={
              selectedCase
                ? "No events recorded for this investigation yet."
                : "Workspace activity will appear here."
            }
          />
        )}
      </section>
    </>
  );
}

function EvidenceModule({ cases, evidence, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function upload(event) {
    event.preventDefault();
    const formElement = event.currentTarget;
    setBusy(true);
    setError("");
    setMessage("");

    try {
      const form = new FormData(event.currentTarget);
      await apiRequest("/api/evidence", { method: "POST", body: form });
      formElement.reset();
      setMessage("Evidence stored and SHA-256 recorded.");
      await onChanged();
    } catch (uploadError) {
      setError(uploadError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <ModuleHeading
        eyebrow="EVIDENCE MANAGEMENT"
        title="Evidence"
        description="Add files to the local evidence workspace and verify their SHA-256 hashes."
      />

      <form className="panel module-form" onSubmit={upload}>
        <label className="form-field">
          <span>Evidence file <b>*</b></span>
          <input type="file" name="file" required />
          <small>
            Files are copied into the project evidence folder and are never
            executed. Maximum size: 25 MB.
          </small>
        </label>

        <label className="form-field">
          <span>Investigation (optional)</span>
          <select name="case_id" defaultValue="">
            <option value="">No investigation linked</option>
            {cases.map((item) => (
              <option key={item.case_id} value={item.case_id}>
                {item.case_id} — {item.name}
              </option>
            ))}
          </select>
        </label>

        {error && <p className="form-error" role="alert">{error}</p>}
        {message && <p className="form-success" role="status">{message}</p>}

        <button className="primary-button" disabled={busy}>
          <Upload size={16} />
          {busy ? "Adding evidence…" : "Add Evidence"}
        </button>
      </form>

      <section className="panel resource-panel">
        <div className="panel-heading">
          <div>
            <h3>Evidence items</h3>
            <p>{evidence.length} item(s) in the workspace</p>
          </div>
        </div>

        {evidence.length ? (
          <div className="resource-list">
            {evidence.map((item) => (
              <article className="resource-row" key={item.evidence_id}>
                <div className="resource-icon purple">
                  <HardDrive size={18} />
                </div>

                <div className="resource-main">
                  <strong>{item.original_name}</strong>
                  <span>
                    {item.case_id || "Unlinked"}
                    {item.case_name ? ` · ${item.case_name}` : ""}
                    {" · "}
                    {formatBytes(item.size_bytes)}
                    {" · "}
                    {formatDate(item.uploaded_at)}
                  </span>
                  <code>SHA-256: {item.sha256}</code>
                </div>

                <a
                  className="secondary-button evidence-download"
                  href={`/api/evidence/${item.evidence_id}/download`}
                  download
                >
                  <Download size={15} /> Download
                </a>
              </article>
            ))}
          </div>
        ) : (
          <ResourceEmptyState text="No evidence added yet. Choose a file above to start." />
        )}
      </section>
    </>
  );
}
function AnalysisModule({ evidence, runs, onChanged }) {
  const [selected, setSelected] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [latest, setLatest] = useState(null);

  async function runScan(event) {
    event.preventDefault();
    if (!selected) return;

    setBusy(true);
    setError("");

    try {
      const result = await apiRequest(
        `/api/evidence/${encodeURIComponent(selected)}/analyze`,
        { method: "POST" }
      );
      setLatest(result);
      await onChanged();
    } catch (scanError) {
      setError(scanError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <ModuleHeading
        eyebrow="RULE-BASED REVIEW"
        title="Analysis"
        description="Run a small, explainable text scan against stored evidence. Results are suggestions for manual review."
      />

      <form className="panel module-form inline-form" onSubmit={runScan}>
        <label className="form-field grow-field">
          <span>Evidence to scan</span>
          <select
            required
            value={selected}
            onChange={(event) => setSelected(event.target.value)}
          >
            <option value="">Select an evidence item</option>
            {evidence.map((item) => (
              <option key={item.evidence_id} value={item.evidence_id}>
                {item.original_name} · {item.case_id || "Unlinked"}
              </option>
            ))}
          </select>
        </label>

        <button
          className="primary-button"
          disabled={busy || evidence.length === 0}
        >
          <ScanSearch size={16} />
          {busy ? "Scanning…" : "Run rule scan"}
        </button>

        {error && <p className="form-error" role="alert">{error}</p>}
      </form>

      <div className="notice-panel">
        <ShieldCheck size={18} />
        <div>
          <strong>What this scan checks</strong>
          <p>
            It searches readable text for IPv4 addresses and a short list
            of suspicious command keywords. It does not use AI, unpack
            files, or execute evidence. A match is not proof of malicious
            activity.
          </p>
        </div>
      </div>

      {latest && <AnalysisResult result={latest} />}

      <section className="panel resource-panel">
        <div className="panel-heading">
          <div>
            <h3>Previous scans</h3>
            <p>Each scan is saved to the timeline.</p>
          </div>
        </div>

        {runs.length ? (
          <div className="resource-list">
            {runs.map((run) => (
              <article className="resource-row" key={run.run_id}>
                <div className="resource-icon blue">
                  <ScanSearch size={18} />
                </div>
                <div className="resource-main">
                  <strong>{run.original_name}</strong>
                  <span>
                    {formatDate(run.created_at)} · {run.summary}
                  </span>
                  {run.indicators?.length > 0 && (
                    <div className="tag-list">
                      {run.indicators.map((indicator, index) => (
                        <span
                          className="data-tag"
                          key={`${run.run_id}-${index}`}
                        >
                          {indicator.type}: {indicator.value}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </article>
            ))}
          </div>
        ) : (
          <ResourceEmptyState text="No analysis runs yet." />
        )}
      </section>
    </>
  );
}

function AnalysisResult({ result }) {
  const indicators = result.indicators || [];

  return (
    <section className="panel result-panel">
      <h3>Scan result</h3>
      <p>{result.summary}</p>
      {indicators.length > 0 && (
        <ul className="indicator-list">
          {indicators.map((item, index) => (
            <li key={`${item.value}-${index}`}>
              <strong>{item.type}: {item.value}</strong>
              <span>{item.reason}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function formatBytes(size) {
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(value) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString();
}

export default App;
