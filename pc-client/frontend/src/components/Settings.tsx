// Settings 组件

import React, { useState, useEffect } from 'react';
import type { AppSettings } from '../types/api';

interface SettingsProps {
  settings: AppSettings | null;
  onSave: (settings: Partial<AppSettings>) => Promise<boolean>;
  isLoading?: boolean;
}

export function Settings({ settings, onSave, isLoading = false }: SettingsProps) {
  const [formData, setFormData] = useState<Partial<AppSettings>>({});
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (settings) {
      setFormData(settings);
    }
  }, [settings]);

  const handleChange = (key: keyof AppSettings, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    setIsSaving(true);
    await onSave(formData);
    setIsSaving(false);
  };

  if (isLoading) {
    return (
      <div className="p-6 bg-bg-card rounded-lg border border-divider">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-divider rounded w-1/4" />
          <div className="h-10 bg-divider rounded" />
          <div className="h-10 bg-divider rounded" />
          <div className="h-10 bg-divider rounded" />
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 bg-bg-card rounded-lg border border-divider">
      <h3 className="text-lg font-medium text-text-primary mb-6">设置</h3>
      
      <div className="space-y-6">
        {/* 下载路径 */}
        <div>
          <label className="block text-sm text-text-secondary mb-2">下载路径</label>
          <input
            type="text"
            value={formData.download_path || ''}
            onChange={(e) => handleChange('download_path', e.target.value)}
            placeholder="选择下载文件保存路径"
            className="w-full px-4 py-2 bg-bg border border-divider rounded-lg text-text-primary placeholder-text-secondary focus:outline-none focus:border-accent transition-colors"
          />
        </div>

        {/* 自动安装 */}
        <div className="flex items-center justify-between">
          <div>
            <label className="text-text-primary">自动安装</label>
            <p className="text-sm text-text-secondary">下载完成后自动开始安装</p>
          </div>
          <button
            onClick={() => handleChange('auto_install', !formData.auto_install)}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              formData.auto_install ? 'bg-accent' : 'bg-divider'
            }`}
          >
            <span
              className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                formData.auto_install ? 'left-7' : 'left-1'
              }`}
            />
          </button>
        </div>

        {/* 通知 */}
        <div className="flex items-center justify-between">
          <div>
            <label className="text-text-primary">通知推送</label>
            <p className="text-sm text-text-secondary">安装完成时发送通知</p>
          </div>
          <button
            onClick={() => handleChange('notification_enabled', !formData.notification_enabled)}
            className={`relative w-12 h-6 rounded-full transition-colors ${
              formData.notification_enabled ? 'bg-accent' : 'bg-divider'
            }`}
          >
            <span
              className={`absolute top-1 w-4 h-4 rounded-full bg-white transition-transform ${
                formData.notification_enabled ? 'left-7' : 'left-1'
              }`}
            />
          </button>
        </div>

        {/* PushDeer Key */}
        <div>
          <label className="block text-sm text-text-secondary mb-2">PushDeer Key</label>
          <input
            type="text"
            value={formData.pushdeer_key || ''}
            onChange={(e) => handleChange('pushdeer_key', e.target.value)}
            placeholder="输入 PushDeer 推送 Key"
            className="w-full px-4 py-2 bg-bg border border-divider rounded-lg text-sm text-text-primary placeholder:text-text-secondary outline-none focus:border-accent transition-colors font-mono"
          />
          <p className="text-xs text-text-secondary mt-1">
            用于安装完成/失败时推送通知到手机。在 PushDeer App 中获取 Key。
          </p>
        </div>

        {/* 语言 */}
        <div>
          <label className="block text-sm text-text-secondary mb-2">语言</label>
          <select
            value={formData.language || 'zh-CN'}
            onChange={(e) => handleChange('language', e.target.value)}
            className="w-full px-4 py-2 bg-bg border border-divider rounded-lg text-text-primary focus:outline-none focus:border-accent transition-colors"
          >
            <option value="zh-CN">简体中文</option>
            <option value="zh-TW">繁体中文</option>
            <option value="en">English</option>
          </select>
        </div>

        {/* 主题 */}
        <div>
          <label className="block text-sm text-text-secondary mb-2">主题</label>
          <select
            value={formData.theme || 'dark'}
            onChange={(e) => handleChange('theme', e.target.value)}
            className="w-full px-4 py-2 bg-bg border border-divider rounded-lg text-text-primary focus:outline-none focus:border-accent transition-colors"
          >
            <option value="dark">深色</option>
            <option value="light">浅色</option>
          </select>
        </div>

        {/* 保存按钮 */}
        <div className="flex justify-end pt-4">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-6 py-2 bg-accent hover:bg-accent/80 disabled:bg-divider disabled:text-text-secondary text-white rounded-lg transition-colors font-medium"
          >
            {isSaving ? '保存中...' : '保存设置'}
          </button>
        </div>
      </div>
    </div>
  );
}
