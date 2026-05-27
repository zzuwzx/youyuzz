// Type declarations for the Electron preload API
// Exposed via contextBridge in electron/preload.ts

interface ElectronAPI {
  onPythonLog: (callback: (message: string) => void) => void;
  onPythonReady: (callback: () => void) => void;
  onPythonError: (callback: (message: string) => void) => void;
  removeAllListeners: (channel: string) => void;
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}

export {};
