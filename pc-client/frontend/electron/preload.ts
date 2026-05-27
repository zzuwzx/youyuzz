import { contextBridge, ipcRenderer } from 'electron';

contextBridge.exposeInMainWorld('electronAPI', {
  onPythonLog: (callback: (message: string) => void) => {
    ipcRenderer.on('python:log', (_event, message) => callback(message));
  },
  onPythonReady: (callback: () => void) => {
    ipcRenderer.on('python:ready', () => callback());
  },
  onPythonError: (callback: (message: string) => void) => {
    ipcRenderer.on('python:error', (_event, message) => callback(message));
  },
  removeAllListeners: (channel: string) => {
    ipcRenderer.removeAllListeners(channel);
  },
});
