/**
 * Electron main process - floating window setup.
 */
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');

let mainWindow = null;
const BASE_WIDTH = 500;

function createMainWindow() {
  const { screen } = require('electron');
  const primaryDisplay = screen.getPrimaryDisplay();
  const screenHeight = primaryDisplay.workAreaSize.height;

  const screenWidth = primaryDisplay.workAreaSize.width;

  mainWindow = new BrowserWindow({
    width: BASE_WIDTH,
    height: screenHeight,
    x: Math.round((screenWidth - BASE_WIDTH) / 2),
    y: 0,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });
  mainWindow.loadFile(path.join(__dirname, 'index.html'));
  mainWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
  mainWindow.on('closed', () => { mainWindow = null; });
}

// Track current panel widths
let currentPdfWidth = 0;
let currentRlWidth = 0;

function updateWindowSize() {
  if (!mainWindow) return;
  const bounds = mainWindow.getBounds();
  const totalWidth = BASE_WIDTH + currentPdfWidth + currentRlWidth;

  // Calculate new x position (shift left if PDF panel is open)
  const { screen } = require('electron');
  const screenWidth = screen.getPrimaryDisplay().workAreaSize.width;
  let newX = Math.round((screenWidth - BASE_WIDTH) / 2) - currentPdfWidth;
  newX = Math.max(0, newX);

  mainWindow.setBounds({
    x: newX,
    y: bounds.y,
    width: totalWidth,
    height: bounds.height,
  });
  console.log(`[main] Window resized: pdf=${currentPdfWidth}, rl=${currentRlWidth}, total=${totalWidth}`);
}

// IPC: Expand window when PDF panel opens
ipcMain.on('expand-window-for-pdf', (event, { pdfWidth }) => {
  currentPdfWidth = Math.round(pdfWidth);
  updateWindowSize();
});

// IPC: Expand window when RL panel opens (right side)
ipcMain.on('expand-window-for-rl', (event, { rlWidth }) => {
  currentRlWidth = Math.round(rlWidth);
  updateWindowSize();
});

// IPC: Collapse window when RL panel closes
ipcMain.on('collapse-window-for-rl', () => {
  currentRlWidth = 0;
  updateWindowSize();
});

app.whenReady().then(createMainWindow);
app.on('window-all-closed', () => app.quit());
