"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
electron_1.contextBridge.exposeInMainWorld('electronAPI', {
    onPythonLog: (callback) => {
        electron_1.ipcRenderer.on('python:log', (_event, message) => callback(message));
    },
    onPythonReady: (callback) => {
        electron_1.ipcRenderer.on('python:ready', () => callback());
    },
    onPythonError: (callback) => {
        electron_1.ipcRenderer.on('python:error', (_event, message) => callback(message));
    },
    removeAllListeners: (channel) => {
        electron_1.ipcRenderer.removeAllListeners(channel);
    },
});
