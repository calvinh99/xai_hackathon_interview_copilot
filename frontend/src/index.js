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

// IPC: Expand window when PDF panel opens
ipcMain.on('expand-window-for-pdf', (event, { pdfWidth }) => {
  if (mainWindow) {
    const bounds = mainWindow.getBounds();
    const expandedWidth = BASE_WIDTH + Math.round(pdfWidth);
    // Expand to the left by moving x and increasing width
    const newX = Math.max(0, bounds.x - Math.round(pdfWidth));
    mainWindow.setBounds({
      x: newX,
      y: bounds.y,
      width: expandedWidth,
      height: bounds.height,
    });
    console.log('[main] Expanded window for PDF panel, width:', expandedWidth);
  }
});

app.whenReady().then(createMainWindow);
app.on('window-all-closed', () => app.quit());
