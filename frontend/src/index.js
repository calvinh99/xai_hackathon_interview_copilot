/**
 * Electron main process - Multiple floating windows setup.
 */
const { app, BrowserWindow, ipcMain, screen } = require('electron');
const path = require('path');

let mainWindow;
let questionWindow;
let cheatAlertWindow;

/**
 * Create main control window (can be hidden or minimized)
 */
function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 400,
    height: 600,
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
}

/**
 * Create Question Hints floating window (top-left)
 */
function createQuestionWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  
  questionWindow = new BrowserWindow({
    width: 400,
    height: 500,
    x: 20,  // 20px from left edge
    y: 20,  // 20px from top edge
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });
  
  questionWindow.loadFile(path.join(__dirname, 'question-window.html'));
  questionWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
}

/**
 * Create Cheat Alert floating window (bottom-right)
 */
function createCheatAlertWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;
  
  const windowWidth = 400;
  const windowHeight = 300;
  
  cheatAlertWindow = new BrowserWindow({
    width: windowWidth,
    height: windowHeight,
    x: width - windowWidth - 20,   // 20px from right edge
    y: height - windowHeight - 20, // 20px from bottom edge
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    resizable: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });
  
  cheatAlertWindow.loadFile(path.join(__dirname, 'cheat-alert-window.html'));
  cheatAlertWindow.setVisibleOnAllWorkspaces(true, { visibleOnFullScreen: true });
}

/**
 * IPC handlers for window communication
 */
function setupIPCHandlers() {
  // Send question hints to question window
  ipcMain.on('update-questions', (event, questions) => {
    if (questionWindow && !questionWindow.isDestroyed()) {
      questionWindow.webContents.send('questions-updated', questions);
    }
  });
  
  // Send cheat alerts to cheat window
  ipcMain.on('update-cheats', (event, alerts) => {
    if (cheatAlertWindow && !cheatAlertWindow.isDestroyed()) {
      cheatAlertWindow.webContents.send('cheats-updated', alerts);
    }
  });
  
  // Toggle window visibility
  ipcMain.on('toggle-question-window', () => {
    if (questionWindow) {
      questionWindow.isVisible() ? questionWindow.hide() : questionWindow.show();
    }
  });
  
  ipcMain.on('toggle-cheat-window', () => {
    if (cheatAlertWindow) {
      cheatAlertWindow.isVisible() ? cheatAlertWindow.hide() : cheatAlertWindow.show();
    }
  });
  
  // Close windows
  ipcMain.on('close-window', (event, windowType) => {
    if (windowType === 'question' && questionWindow) {
      questionWindow.close();
    } else if (windowType === 'cheat' && cheatAlertWindow) {
      cheatAlertWindow.close();
    } else if (windowType === 'main' && mainWindow) {
      mainWindow.close();
    }
  });
}

app.whenReady().then(() => {
  createMainWindow();
  createQuestionWindow();
  createCheatAlertWindow();
  setupIPCHandlers();
});

app.on('window-all-closed', () => {
  app.quit();
});
