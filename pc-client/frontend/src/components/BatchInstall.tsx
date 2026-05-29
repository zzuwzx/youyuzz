// BatchInstall 批量安装组件

import React, { useState } from 'react';
import { Crown } from 'lucide-react';
import type { InstallProgress, SubTaskProgress } from '../types/api';

interface BatchInstallProps {
  isVip: boolean;
  onStartBatch: (gameNames: string[]) => void;
  isLoading: boolean;
  progress: InstallProgress | null;
  subTasks: SubTaskProgress[];
  onNavigateVip?: () => void;
}

const STAGE_LABELS: Record<string, string> = {
  queued: '排队中',
  scraping: '搜索中',
  saving_to_disk: '转存中',
  downloading: '下载中',
  classifying: '分类中',
  transferring_mtp: '传输中',
  completed: '已完成',
  failed: '失败',
  cancelled: '已取消',
};

export function BatchInstall({
  isVip,
  onStartBatch,
  isLoading,
  progress,
  subTasks,
  onNavigateVip,
}: BatchInstallProps) {
  const [inputText, setInputText] = useState('');

  const handleStart = () => {
    const names = inputText
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean);
    if (names.length > 0) {
      onStartBatch(names);
    }
  };

  const isInstalling = isLoading || (progress && !['completed', 'failed', 'cancelled'].includes(progress.stage));
  const gameCount = inputText.split('\n').filter((line) => line.trim()).length;

  // 非 VIP 提示
  if (!isVip) {
    return (
      <div className="p-6 bg-bg-card rounded-lg border border-vip-gold/30">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-vip-gold/20 flex items-center justify-center">
            <Crown className="w-5 h-5 text-vip-gold" />
          </div>
          <div>
            <h3 className="text-text-primary font-medium">VIP 专属功能</h3>
            <p className="text-sm text-text-secondary">批量安装需要 VIP 授权</p>
          </div>
        </div>
        <button
          onClick={onNavigateVip}
          className="w-full py-2.5 bg-vip-gold hover:bg-vip-gold/80 text-bg rounded-lg transition-colors font-medium"
        >
          升级 VIP
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 输入区域 */}
      {!isInstalling && (
        <div className="p-6 bg-bg-card rounded-lg border border-divider">
          <h3 className="text-lg font-medium text-text-primary mb-4">批量安装</h3>
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={'每行一个游戏名，例如：\n塞尔达传说\n马力欧赛车\n宝可梦紫'}
            rows={6}
            className="w-full px-4 py-3 bg-bg border border-divider rounded-lg text-sm text-text-primary placeholder:text-text-secondary outline-none focus:border-accent transition-colors resize-none"
            disabled={!!isInstalling}
          />
          <div className="flex items-center justify-between mt-3">
            <span className="text-sm text-text-secondary">
              {gameCount > 0 ? `共 ${gameCount} 个游戏` : '请输入游戏名'}
            </span>
            <button
              onClick={handleStart}
              disabled={gameCount === 0 || !!isInstalling}
              className={`px-6 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                gameCount > 0 && !isInstalling
                  ? 'bg-accent text-white hover:bg-accent/90 active:scale-[0.98]'
                  : 'bg-divider text-text-secondary cursor-not-allowed'
              }`}
            >
              开始批量安装
            </button>
          </div>
        </div>
      )}

      {/* 批量进度 */}
      {progress && isInstalling && (
        <div className="p-6 bg-bg-card rounded-lg border border-divider">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-lg font-medium text-text-primary">批量安装中</h3>
            <span className="text-sm text-text-secondary">
              {progress.completed_files}/{progress.total_files}
            </span>
          </div>

          {/* 总进度条 */}
          <div className="mb-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm text-text-secondary truncate max-w-[200px]">
                {progress.current_file || '准备中...'}
              </span>
              <span className="text-sm text-text-primary font-medium">
                {progress.percent}%
              </span>
            </div>
            <div className="h-2 bg-divider rounded-full overflow-hidden">
              <div
                className="h-full bg-accent transition-all duration-300"
                style={{ width: `${progress.percent}%` }}
              />
            </div>
          </div>

          {/* 当前状态 */}
          {progress.current_file && (
            <div className="text-sm text-text-secondary mb-3">
              <span className="text-accent">
                {STAGE_LABELS[progress.stage] || progress.stage}
              </span>
              {progress.speed && <span className="ml-3">{progress.speed}</span>}
              {progress.eta && <span className="ml-3">剩余 {progress.eta}</span>}
            </div>
          )}

          {/* 子任务列表 */}
          {subTasks.length > 0 && (
            <div className="mt-4 space-y-2 max-h-48 overflow-y-auto">
              {subTasks.map((sub) => (
                <div
                  key={sub.task_id}
                  className="flex items-center gap-2 text-sm p-2 rounded bg-bg/50"
                >
                  <span className="flex-shrink-0 w-5 text-center">
                    {sub.stage === 'completed' ? '✅' :
                     sub.stage === 'failed' ? '❌' :
                     sub.percent > 0 ? '⏳' : '⏸️'}
                  </span>
                  <span className="flex-1 text-text-primary truncate">
                    {sub.game_name}
                  </span>
                  <span className="text-text-secondary text-xs">
                    {sub.stage === 'completed' ? '完成' :
                     sub.stage === 'failed' ? '失败' :
                     `${sub.percent}%`}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* 错误信息 */}
          {progress.error && (
            <div className="mt-3 p-3 bg-error/10 border border-error/30 rounded-lg">
              <p className="text-error text-sm">{progress.error}</p>
            </div>
          )}
        </div>
      )}

      {/* 完成状态 */}
      {progress && progress.stage === 'completed' && !isInstalling && (
        <div className="p-6 bg-bg-card rounded-lg border border-success/30">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-full bg-success/20 flex items-center justify-center">
              <svg className="w-6 h-6 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <h3 className="text-lg font-medium text-text-primary">批量安装完成</h3>
              <p className="text-sm text-text-secondary">
                {progress.error || `成功安装 ${progress.completed_files} 个游戏`}
              </p>
            </div>
          </div>
          {subTasks.length > 0 && (
            <div className="space-y-1 mt-3">
              {subTasks.map((sub) => (
                <div key={sub.task_id} className="flex items-center gap-2 text-sm">
                  <span>{sub.stage === 'completed' ? '✅' : '❌'}</span>
                  <span className="text-text-primary">{sub.game_name}</span>
                  {sub.error && <span className="text-error text-xs">({sub.error})</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 失败状态 */}
      {progress && progress.stage === 'failed' && !isInstalling && (
        <div className="p-6 bg-error/10 border border-error/30 rounded-lg">
          <h3 className="text-lg font-medium text-text-primary mb-2">批量安装失败</h3>
          <p className="text-error text-sm">{progress.error || '未知错误'}</p>
        </div>
      )}
    </div>
  );
}
