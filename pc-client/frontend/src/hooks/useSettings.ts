// 设置 Hook

import { useState, useCallback, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { AppSettings, LoadingState } from '../types/api';

export function useSettings() {
  const [state, setState] = useState<LoadingState>('idle');
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 加载设置
  const loadSettings = useCallback(async () => {
    setState('loading');
    setError(null);

    const response = await apiClient.getSettings();

    if (response.success && response.data) {
      setSettings(response.data);
      setState('success');
    } else {
      setError(response.error || '加载设置失败');
      setState('error');
    }
  }, []);

  // 保存设置
  const saveSettings = useCallback(async (newSettings: Partial<AppSettings>) => {
    setState('loading');
    setError(null);

    const response = await apiClient.saveSettings(newSettings);

    if (response.success) {
      // 重新加载设置
      await loadSettings();
      return true;
    } else {
      setError(response.error || '保存设置失败');
      setState('error');
      return false;
    }
  }, [loadSettings]);

  // 重置状态
  const reset = useCallback(() => {
    setState('idle');
    setSettings(null);
    setError(null);
  }, []);

  return {
    state,
    settings,
    error,
    loadSettings,
    saveSettings,
    reset,
    isLoading: state === 'loading',
    isLoaded: state === 'success' && settings !== null,
  };
}
