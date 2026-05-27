import { ChildProcess, spawn } from 'child_process';
import { EventEmitter } from 'events';
import path from 'path';
import fs from 'fs';

export interface PythonBridgeOptions {
  pythonPath?: string;
  scriptPath?: string;
  exePath?: string;
  cwd?: string;
  port?: number;
}

export class PythonBridge extends EventEmitter {
  private proc: ChildProcess | null = null;
  private _isRunning = false;
  private pythonPath: string;
  private scriptPath: string;
  private exePath: string;
  private cwd: string;
  private port: number;
  private isPackaged: boolean;

  constructor(options: PythonBridgeOptions = {}) {
    super();
    
    // 检测是否为打包环境
    this.isPackaged = process.resourcesPath !== undefined;
    
    const projectRoot = path.resolve(__dirname, '..', '..');
    
    if (this.isPackaged) {
      // 打包后：使用 backend.exe
      this.exePath = options.exePath
        ?? path.join(process.resourcesPath, 'backend', 'backend.exe');
      this.cwd = options.cwd
        ?? path.join(process.resourcesPath, 'backend');
      // 打包模式下不使用 pythonPath 和 scriptPath
      this.pythonPath = '';
      this.scriptPath = '';
    } else {
      // 开发环境：使用 venv 中的 python
      this.pythonPath = options.pythonPath
        ?? path.join(projectRoot, 'backend', 'venv', 'Scripts', 'python.exe');
      this.scriptPath = options.scriptPath
        ?? path.join(projectRoot, 'backend', 'main.py');
      this.cwd = options.cwd
        ?? path.join(projectRoot, 'backend');
      this.exePath = '';
    }
    
    this.port = options.port ?? 18888;
  }

  get isRunning(): boolean {
    return this._isRunning;
  }

  start(): void {
    if (this._isRunning) {
      this.emit('log', '[pythonBridge] already running, skip start');
      return;
    }

    const env = {
      ...process.env,
      PYTHONUNBUFFERED: '1',
    };

    let command: string;
    let args: string[];

    if (this.isPackaged) {
      // 打包后：直接运行 backend.exe
      command = this.exePath;
      args = [];
      this.emit('log', `[pythonBridge] spawning packaged backend: ${command}`);
    } else {
      // 开发环境：运行 python main.py
      command = this.pythonPath;
      args = [this.scriptPath];
      this.emit('log', `[pythonBridge] spawning: ${command} ${args.join(' ')}`);
    }
    
    this.emit('log', `[pythonBridge] cwd: ${this.cwd}`);
    this.emit('log', `[pythonBridge] isPackaged: ${this.isPackaged}`);

    // 检查文件是否存在
    if (!fs.existsSync(command)) {
      this.emit('error', `[pythonBridge] executable not found: ${command}`);
      this.emit('exit', -1);
      return;
    }

    this.proc = spawn(command, args, {
      cwd: this.cwd,
      env,
      windowsHide: true,
    });

    this._isRunning = true;

    // stdout line buffer
    this.proc.stdout?.on('data', (data: Buffer) => {
      const lines = data.toString().split(/\r?\n/);
      for (const line of lines) {
        if (line.trim()) {
          this.emit('log', line);
        }
      }
    });

    // stderr line buffer
    this.proc.stderr?.on('data', (data: Buffer) => {
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

  stop(): Promise<void> {
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
