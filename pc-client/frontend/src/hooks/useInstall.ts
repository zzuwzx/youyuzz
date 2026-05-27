// 安装 Hook

import { useState, useCallback, useRef, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { InstallProgress, LoadingState } from '../types/api';

export function useInstall() {
  const [state, setState] = useState<LoadingState>('idle');
  const [progress, setProgress] = useState<InstallProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollingRef = useRef<number | null>(null);

  // 停止轮询
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  // 开始轮询进度
  const startPolling = useCallback((taskId: string) => {
    stopPolling();
    
    const poll = async () => {
      const response = await apiClient.getInstallProgress(taskId);
      
      if (response.success && response.data) {
        setProgress(response.data);
        
        if (response.data.status === 'completed' || response.data.status === 'failed') {
          stopPolling();
          setState(response.data.status === 'completed' ? 'success' : 'error');
          if (response.data.status === 'failed') {
            setError(response.data.error || '安装失败');
          }
        }
      } else {
        setError(response.error || '获取进度失败');
        stopPolling();
        setState('error');
      }
    };

    // 立即执行一次
    poll();
    
    // 每秒轮询
    pollingRef.current = setInterval(poll, 1000) as unknown as number;
  }, [stopPolling]);

  // 开始安装
  const startInstall = useCallback(async (gameUrl: string, installOrder?: string[]) => {
    setState('loading');
    setError(null);
    setProgress(null);

    const response = await apiClient.startInstall({
      game_url: gameUrl,
      install_order: installOrder,
    });

    if (response.success && response.data) {
      startPolling(response.data.task_id);
    } else {
      setError(response.error || '启动安装失败');
      setState('error');
    }
  }, [startPolling]);

  // 本地安装
  const localInstall = useCallback(async (folderPath: string) => {
    setState('loading');
    setError(null);
    setProgress(null);

    const response = await apiClient.localInstall(folderPath);

    if (response.success && response.data) {
      startPolling(response.data.task_id);
    } else {
      setError(response.error || '启动本地安装失败');
      setState('error');
    }
  }, [startPolling]);

  // 重置状态
  const reset = useCallback(() => {
    stopPolling();
    setState('idle');
    setProgress(null);
    setError(null);
  }, [stopPolling]);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  return {
    state,
    progress,
    error,
    startInstall,
    localInstall,
    reset,
    isLoading: state === 'loading',
    isCompleted: state === 'success',
    isFailed: state === 'error',
  };
}
