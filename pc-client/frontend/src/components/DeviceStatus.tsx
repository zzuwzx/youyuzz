// DeviceStatus 组件

import React from 'react';
import type { SwitchDevice } from '../types/api';

interface DeviceStatusProps {
  device: SwitchDevice | null;
  isLoading: boolean;
  onRefresh: () => void;
}

export function DeviceStatus({ device, isLoading, onRefresh }: DeviceStatusProps) {
  if (isLoading) {
    return (
      <div className="p-4 bg-bg-card rounded-lg border border-divider">
        <div className="flex items-center gap-3">
          <div className="w-3 h-3 rounded-full bg-text-secondary animate-pulse" />
          <span className="text-text-secondary">检测设备中...</span>
        </div>
      </div>
    );
  }

  if (!device) {
    return (
      <div className="p-4 bg-bg-card rounded-lg border border-divider">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-error" />
            <span className="text-text-secondary">未检测到设备</span>
          </div>
          <button
            onClick={onRefresh}
            className="px-3 py-1 bg-accent-secondary hover:bg-accent text-white rounded text-sm transition-colors"
          >
            重新检测
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 bg-bg-card rounded-lg border border-divider">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className={`w-3 h-3 rounded-full ${device.connected ? 'bg-success' : 'bg-error'}`} />
          <span className="text-text-primary font-medium">
            {device.connected ? 'Switch 已连接' : 'Switch 未连接'}
          </span>
        </div>
        <button
          onClick={onRefresh}
          className="p-1 hover:bg-divider rounded transition-colors"
          title="刷新"
        >
          <svg className="w-4 h-4 text-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>

      {device.connected && (
        <div className="space-y-2 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">设备名称:</span>
            <span className="text-text-primary">{device.device_name || 'Unknown'}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">DBI 模式:</span>
            <span className={device.dbi_mode ? 'text-success' : 'text-warning'}>
              {device.dbi_mode ? '已启用' : '未启用'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-text-secondary">TF 卡:</span>
            <span className={device.tf_card?.inserted ? 'text-success' : 'text-warning'}>
              {device.tf_card?.inserted ? '已插入' : '未插入'}
            </span>
          </div>
          {device.tf_card?.inserted && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-text-secondary">总空间:</span>
                <span className="text-text-primary">
                  {formatBytes(device.tf_card.total_space)}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-text-secondary">可用空间:</span>
                <span className="text-text-primary">
                  {formatBytes(device.tf_card.free_space)}
                </span>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}
