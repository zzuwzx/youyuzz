import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';
import fs from 'fs';
import http from 'http';
import { PythonBridge } from './pythonBridge';

const isDev = !app.isPackaged;
const HEALTH_URL = 'http://127.0.0.1:18888/api/health';
const HEALTH_INTERVAL_MS = 500;
const HEALTH_TIMEOUT_MS = 30_000;
const MAX_RESTART_ATTEMPTS = 3;
const RESTART_DELAY_MS = 2000;

let mainWindow: BrowserWindow | null = null;
let pythonBridge: PythonBridge | null = null;
let logStream: fs.WriteStream | null = null;
let restartCount = 0;
let isQuitting = false;

// ──────────────────────────────────────────────
//  Logging
// ──────────────────────────────────────────────

function getLogFilePath(): string {
  const logDir = path.resolve(__dirname, '..', 'logs');
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  return path.join(logDir, `python-${today}.log`);
}

function initLogStream(): void {
  const logPath = getLogFilePath();
  logStream = fs.createWriteStream(logPath, { flags: 'a' });
  console.log(`[main] log file: ${logPath}`);
}

function writeLog(message: string): void {
  const timestamp = new Date().toISOString();
  const line = `[${timestamp}] ${message}\n`;
  logStream?.write(line);
  // Forward to renderer via IPC
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('python:log', message);
  }
}

function writeError(message: string): void {
  const timestamp = new Date().toISOString();
  const line = `[${timestamp}] ERROR: ${message}\n`;
  logStream?.write(line);
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('python:error', message);
  }
}

// ──────────────────────────────────────────────
//  Window
// ──────────────────────────────────────────────

function createWindow(): void {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 1000,
    minHeight: 700,
    show: false,
    backgroundColor: '#1A1A2E',
    title: '鱿郁仔仔',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

// ──────────────────────────────────────────────
//  Health Check
// ──────────────────────────────────────────────

function checkHealth(): Promise<boolean> {
  return new Promise((resolve) => {
    const req = http.get(HEALTH_URL, (res) => {
      res.resume();
      if (res.statusCode === 200) {
        resolve(true);
      } else {
        resolve(false);
      }
    });
    req.on('error', () => resolve(false));
    req.setTimeout(2000, () => {
      req.destroy();
      resolve(false);
    });
  });
}

async function waitForHealthy(): Promise<boolean> {
  const start = Date.now();
  while (Date.now() - start < HEALTH_TIMEOUT_MS) {
    const ok = await checkHealth();
    if (ok) {
      return true;
    }
    await new Promise((r) => setTimeout(r, HEALTH_INTERVAL_MS));
  }
  return false;
}

// ──────────────────────────────────────────────
//  Python Process Management
// ──────────────────────────────────────────────

function startPython(): void {
  pythonBridge = new PythonBridge();

  pythonBridge.on('log', (msg: string) => {
    writeLog(msg);
  });

  pythonBridge.on('error', (msg: string) => {
    writeError(msg);
  });

  pythonBridge.on('exit', (code: number | null) => {
    writeLog(`[main] Python exited with code ${code}`);
    if (!isQuitting && code !== 0 && restartCount < MAX_RESTART_ATTEMPTS) {
      restartCount++;
      writeLog(`[main] auto restart (${restartCount}/${MAX_RESTART_ATTEMPTS}) in ${RESTART_DELAY_MS}ms...`);
      setTimeout(() => startPython(), RESTART_DELAY_MS);
    } else if (!isQuitting && restartCount >= MAX_RESTART_ATTEMPTS) {
      writeError('[main] max restart attempts reached, giving up');
      mainWindow?.webContents.send('python:error', '后端多次崩溃，请重启应用');
    }
  });

  pythonBridge.start();

  // Wait for health, then show window
  waitForHealthy().then((healthy) => {
    if (healthy) {
      restartCount = 0;
      writeLog('[main] backend healthy, notifying renderer');
      mainWindow?.webContents.send('python:ready');

      const loadUrl = isDev
        ? 'http://localhost:5173'
        : `file://${path.join(__dirname, '..', 'dist', 'index.html')}`;

      mainWindow?.loadURL(loadUrl);
      mainWindow?.show();

      if (isDev) {
        mainWindow?.webContents.openDevTools({ mode: 'detach' });
      }
    } else {
      writeError('[main] health check timed out');
      mainWindow?.webContents.send('python:error', '后端启动超时');
      // Show window anyway so user can see the error
      mainWindow?.show();
    }
  });
}

// ──────────────────────────────────────────────
//  App Lifecycle
// ──────────────────────────────────────────────

app.whenReady().then(() => {
  initLogStream();
  createWindow();
  startPython();
});

// Graceful exit
app.on('before-quit', async (e) => {
  if (isQuitting) return;
  isQuitting = true;
  e.preventDefault();

  writeLog('[main] app quitting, stopping Python...');
  if (pythonBridge) {
    await pythonBridge.stop();
  }

  logStream?.end();
  app.quit();
});

// macOS: re-create window on dock click
app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});
