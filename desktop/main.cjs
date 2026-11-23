const { app, BrowserWindow, dialog } = require("electron");
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");
const { spawn } = require("node:child_process");

let apiProcess;
let webServer;
let mainWindow;
let stopping = false;

const mimeTypes = {
  ".css": "text/css; charset=utf-8",
  ".html": "text/html; charset=utf-8",
  ".ico": "image/x-icon",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
};

function reservePort() {
  return new Promise((resolve, reject) => {
    const server = http.createServer();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      server.close((error) => (error ? reject(error) : resolve(port)));
    });
  });
}

function startApi(port, userData) {
  const binary = path.join(process.resourcesPath, "backend", "CyberTriageAPI");
  const databasePath = path.join(userData, "cybertriage.db");
  const evidencePath = path.join(userData, "evidence");
  fs.mkdirSync(evidencePath, { recursive: true });
  apiProcess = spawn(binary, [], {
    env: {
      ...process.env,
      DATABASE_URL: `sqlite:///${databasePath}`,
      CYBERTRIAGE_EVIDENCE_DIR: evidencePath,
      CYBERTRIAGE_HOST: "127.0.0.1",
      CYBERTRIAGE_PORT: String(port),
      CYBERTRIAGE_COOKIE_SECURE: "0",
      CYBERTRIAGE_SEED_DEMO_DATA: "0",
    },
    stdio: "ignore",
  });
  apiProcess.once("error", (error) => {
    if (!stopping) dialog.showErrorBox("CyberTriage could not start", error.message);
  });
}

async function waitForApi(port) {
  const until = Date.now() + 30000;
  while (Date.now() < until) {
    if (apiProcess?.exitCode !== null && apiProcess?.exitCode !== undefined) {
      throw new Error(`The local API exited with code ${apiProcess.exitCode}.`);
    }
    try {
      const response = await fetch(`http://127.0.0.1:${port}/api/health`);
      if (response.ok) return;
    } catch (_) {
      // The bundled API can take a few seconds to initialize SQLite.
    }
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error("The local API did not become ready within 30 seconds.");
}

function startWebServer(apiPort) {
  const root = path.join(app.getAppPath(), "frontend", "dist");
  webServer = http.createServer((request, response) => {
    const url = new URL(request.url, "http://127.0.0.1");
    if (url.pathname === "/api" || url.pathname.startsWith("/api/")) {
      const { origin: _origin, referer: _referer, ...forwardHeaders } = request.headers;
      const proxy = http.request(
        {
          hostname: "127.0.0.1",
          port: apiPort,
          path: `${url.pathname}${url.search}`,
          method: request.method,
          // The desktop proxy makes the API same-origin to the renderer. Drop
          // browser origin headers so the development-only CORS allowlist
          // does not reject the packaged app's ephemeral port.
          headers: { ...forwardHeaders, host: `127.0.0.1:${apiPort}` },
        },
        (apiResponse) => {
          response.writeHead(apiResponse.statusCode || 502, apiResponse.headers);
          apiResponse.pipe(response);
        },
      );
      proxy.on("error", () => {
        if (!response.headersSent) response.writeHead(502);
        response.end("CyberTriage API unavailable");
      });
      request.pipe(proxy);
      return;
    }

    let pathname;
    try {
      pathname = decodeURIComponent(url.pathname);
    } catch (_) {
      response.writeHead(400).end("Invalid path");
      return;
    }
    const candidate = path.resolve(root, `.${pathname}`);
    const safePath = candidate.startsWith(`${path.resolve(root)}${path.sep}`)
      ? candidate
      : path.join(root, "index.html");
    const filePath = fs.existsSync(safePath) && fs.statSync(safePath).isFile()
      ? safePath
      : path.join(root, "index.html");
    response.writeHead(200, {
      "Content-Type": mimeTypes[path.extname(filePath)] || "application/octet-stream",
      "X-Content-Type-Options": "nosniff",
    });
    fs.createReadStream(filePath).pipe(response);
  });

  return new Promise((resolve, reject) => {
    webServer.once("error", reject);
    webServer.listen(0, "127.0.0.1", () => resolve(webServer.address().port));
  });
}

async function createMainWindow() {
  const apiPort = await reservePort();
  startApi(apiPort, app.getPath("userData"));
  await waitForApi(apiPort);
  const webPort = await startWebServer(apiPort);
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 960,
    minWidth: 1024,
    minHeight: 700,
    title: "CyberTriage",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  await mainWindow.loadURL(`http://127.0.0.1:${webPort}`);
  mainWindow.on("closed", () => (mainWindow = null));
}

async function stopServices() {
  stopping = true;
  if (webServer) await new Promise((resolve) => webServer.close(resolve));
  if (apiProcess && apiProcess.exitCode === null) {
    apiProcess.kill("SIGTERM");
    await Promise.race([
      new Promise((resolve) => apiProcess.once("exit", resolve)),
      new Promise((resolve) => setTimeout(resolve, 3000)),
    ]);
    if (apiProcess.exitCode === null) apiProcess.kill("SIGKILL");
  }
}

app.whenReady().then(async () => {
  try {
    await createMainWindow();
  } catch (error) {
    await stopServices();
    dialog.showErrorBox("CyberTriage could not start", error.message);
    app.quit();
  }
});

app.on("before-quit", (event) => {
  if (!stopping) {
    event.preventDefault();
    stopServices().finally(() => app.quit());
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createMainWindow().catch((error) => {
    dialog.showErrorBox("CyberTriage could not restart", error.message);
  });
});
