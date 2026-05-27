// InstallProgress 组件

import React from 'react';
import type { InstallProgress as InstallProgressType } from '../types/api';

interface InstallProgressProps {
  progress: InstallProgressType;
  onCancel?: () => void;
}

export function InstallProgress({ progress, onCancel }: InstallProgressProps) {
  const statusText = {
    pending: '等待中...',
    downloading: '下载中...',
    transferring: '传输中...',
    completed: '安装完成',
    failed: '安装失败',
  };

  const statusColor = {
    pending: 'text-text-secondary',
    downloading: 'text-accent',
    transferring: 'text-accent',
    completed: 'text-success',
    failed: 'text-error',
  };

  return (
    <div className="p-6 bg-bg-card rounded-lg border border-divider">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-text-primary">安装进度</h3>
        <span className={`text-sm font-medium ${statusColor[progress.status]}`}>
          {statusText[progress.status]}
        </span>
      </div>

      {/* 进度条 */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-text-secondary">
            {progress.current_file || '准备中...'}
          </span>
          <span className="text-sm text-text-primary font-medium">{progress.progress}%</span>
        </div>
        <div className="h-2 bg-divider rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              progress.status === 'failed' ? 'bg-error' : 'bg-accent'
            }`}
            style={{ width: `${progress.progress}%` }}
          />
        </div>
      </div>

      {/* 详细信息 */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-text-secondary">文件进度:</span>
          <span className="ml-2 text-text-primary">
            {progress.current_file ? `${progress.current_file}` : '-'} / {progress.total_files}
          </span>
        </div>
        <div>
          <span className="text-text-secondary">速度:</span>
          <span className="ml-2 text-text-primary">{progress.speed || '-'}</span>
        </div>
        <div>
          <span className="text-text-secondary">预计剩余:</span>
          <span className="ml-2 text-text-primary">{progress.eta || '-'}</span>
        </div>
      </div>

      {/* 错误信息 */}
      {progress.status === 'failed' && progress.error && (
        <div className="mt-4 p-3 bg-error/10 border border-error/30 rounded-lg">
          <p className="text-error text-sm">{progress.error}</p>
        </div>
      )}

      {/* 操作按钮 */}
      {progress.status !== 'completed' && progress.status !== 'failed' && onCancel && (
        <div className="mt-4 flex justify-end">
          <button
            onClick={onCancel}
            className="px-4 py-2 bg-error/20 hover:bg-error/30 text-error rounded-lg text-sm transition-colors"
          >
            取消安装
          </button>
        </div>
      )}
    </div>
  );
}
