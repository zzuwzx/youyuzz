"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
exports.PythonBridge = void 0;
const child_process_1 = require("child_process");
const events_1 = require("events");
const path_1 = __importDefault(require("path"));
const fs_1 = __importDefault(require("fs"));
class PythonBridge extends events_1.EventEmitter {
    constructor(options = {}) {
        super();
        this.proc = null;
        this._isRunning = false;
        // 检测是否为打包环境
        this.isPackaged = process.resourcesPath !== undefined;
        const projectRoot = path_1.default.resolve(__dirname, '..', '..');
        if (this.isPackaged) {
            // 打包后：使用 backend.exe
            this.exePath = options.exePath
                ?? path_1.default.join(process.resourcesPath, 'backend', 'backend.exe');
            this.cwd = options.cwd
                ?? path_1.default.join(process.resourcesPath, 'backend');
            // 打包模式下不使用 pythonPath 和 scriptPath
            this.pythonPath = '';
            this.scriptPath = '';
        }
        else {
            // 开发环境：使用 venv 中的 python
            this.pythonPath = options.pythonPath
                ?? path_1.default.join(projectRoot, 'backend', 'venv', 'Scripts', 'python.exe');
            this.scriptPath = options.scriptPath
                ?? path_1.default.join(projectRoot, 'backend', 'main.py');
            this.cwd = options.cwd
                ?? path_1.default.join(projectRoot, 'backend');
            this.exePath = '';
        }
        this.port = options.port ?? 18888;
    }
    get isRunning() {
        return this._isRunning;
    }
    start() {
        if (this._isRunning) {
            this.emit('log', '[pythonBridge] already running, skip start');
            return;
        }
        const env = {
            ...process.env,
            PYTHONUNBUFFERED: '1',
        };
        let command;
        let args;
        if (this.isPackaged) {
            // 打包后：直接运行 backend.exe
            command = this.exePath;
            args = [];
            this.emit('log', `[pythonBridge] spawning packaged backend: ${command}`);
        }
        else {
            // 开发环境：运行 python main.py
            command = this.pythonPath;
            args = [this.scriptPath];
            this.emit('log', `[pythonBridge] spawning: ${command} ${args.join(' ')}`);
        }
        this.emit('log', `[pythonBridge] cwd: ${this.cwd}`);
        this.emit('log', `[pythonBridge] isPackaged: ${this.isPackaged}`);
        // 检查文件是否存在
        if (!fs_1.default.existsSync(command)) {
            this.emit('error', `[pythonBridge] executable not found: ${command}`);
            this.emit('exit', -1);
            return;
        }
        this.proc = (0, child_process_1.spawn)(command, args, {
            cwd: this.cwd,
            env,
            windowsHide: true,
        });
        this._isRunning = true;
        // stdout line buffer
        this.proc.stdout?.on('data', (data) => {
            const lines = data.toString().split(/\r?\n/);
            for (const line of lines) {
                if (line.trim()) {
                    this.emit('log', line);
                }
            }
        });
        // stderr line buffer
        this.proc.stderr?.on('data', (data) => {
            const lines = data.toString().split(/\r?\n/);
            for (const line of lines) {
                if (line.trim()) {
                    this.emit('error', line);
                }
            }
        });
        this.proc.on('close', (code) => {
            this._isRunning = false;
            this.proc = null;
            this.emit('log', `[pythonBridge] process exited with code ${code}`);
            this.emit('exit', code);
        });
        this.proc.on('error', (err) => {
            this._isRunning = false;
            this.proc = null;
            this.emit('error', `[pythonBridge] spawn error: ${err.message}`);
            this.emit('exit', -1);
        });
    }
    stop() {
        return new Promise((resolve) => {
            if (!this.proc || !this._isRunning) {
                resolve();
                return;
            }
            this.emit('log', '[pythonBridge] stopping python process...');
            // Force kill after 5s timeout
            const timeout = setTimeout(() => {
                if (this.proc) {
                    this.emit('log', '[pythonBridge] SIGTERM timeout, force killing');
                    this.proc.kill('SIGKILL');
                }
            }, 5000);
            this.proc.once('close', () => {
                clearTimeout(timeout);
                resolve();
            });
            // Try graceful shutdown first
            this.proc.kill('SIGTERM');
        });
    }
}
exports.PythonBridge = PythonBridge;
