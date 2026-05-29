// InstallProgress 组件

import React from 'react';
import type { InstallProgress as InstallProgressType } from '../types/api';

interface InstallProgressProps {
  progress: InstallProgressType;
  onCancel?: () => void;
}

const STAGE_TEXT: Record<string, string> = {
  queued: '排队中...',
  scraping: '搜索中...',
  saving_to_disk: '转存中...',
  downloading: '下载中...',
  classifying: '分类中...',
  transferring_mtp: '传输中...',
  transferring: '传输中...',
  completed: '安装完成',
  failed: '安装失败',
  cancelled: '已取消',
};

const STAGE_COLOR: Record<string, string> = {
  queued: 'text-text-secondary',
  scraping: 'text-accent',
  saving_to_disk: 'text-accent',
  downloading: 'text-accent',
  classifying: 'text-accent',
  transferring_mtp: 'text-accent',
  transferring: 'text-accent',
  completed: 'text-success',
  failed: 'text-error',
  cancelled: 'text-text-secondary',
};

export function InstallProgress({ progress, onCancel }: InstallProgressProps) {
  return (
    <div className="p-6 bg-bg-card rounded-lg border border-divider">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-text-primary">安装进度</h3>
        <span className={`text-sm font-medium ${STAGE_COLOR[progress.stage] || 'text-text-secondary'}`}>
          {STAGE_TEXT[progress.stage] || progress.stage}
        </span>
      </div>

      {/* 进度条 */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-text-secondary">
            {progress.current_file || '准备中...'}
          </span>
          <span className="text-sm text-text-primary font-medium">{progress.percent}%</span>
        </div>
        <div className="h-2 bg-divider rounded-full overflow-hidden">
          <div
            className={`h-full transition-all duration-300 ${
              progress.stage === 'failed' ? 'bg-error' : 'bg-accent'
            }`}
            style={{ width: `${progress.percent}%` }}
          />
        </div>
      </div>

      {/* 详细信息 */}
      <div className="grid grid-cols-2 gap-4 text-sm">
        <div>
          <span className="text-text-secondary">文件进度:</span>
          <span className="ml-2 text-text-primary">
            {progress.completed_files} / {progress.total_files}
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
      {progress.stage === 'failed' && progress.error && (
        <div className="mt-4 p-3 bg-error/10 border border-error/30 rounded-lg">
          <p className="text-error text-sm">{progress.error}</p>
        </div>
      )}

      {/* 操作按钮 */}
      {progress.stage !== 'completed' && progress.stage !== 'failed' && progress.stage !== 'cancelled' && onCancel && (
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
