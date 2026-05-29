// 安装 Hook — 使用 SSE 实时推送

import { useState, useCallback, useRef, useEffect } from 'react';
import { apiClient } from '../api/client';
import type { InstallProgress, SubTaskProgress, LoadingState } from '../types/api';

export function useInstall() {
  const [state, setState] = useState<LoadingState>('idle');
  const [progress, setProgress] = useState<InstallProgress | null>(null);
  const [subTasks, setSubTasks] = useState<SubTaskProgress[]>([]);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);
  const currentTaskRef = useRef<string | null>(null);

  // 关闭 SSE 连接
  const closeSSE = useCallback(() => {
    if (esRef.current) {
      esRef.current.close();
      esRef.current = null;
    }
  }, []);

  // 启动 SSE 连接
  const startSSE = useCallback((taskId: string) => {
    closeSSE();
    currentTaskRef.current = taskId;

    const es = new EventSource(`/api/install/${taskId}/stream`);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as InstallProgress;
        setProgress(data);

        // 更新子任务
        if (data.sub_tasks && data.sub_tasks.length > 0) {
          setSubTasks(data.sub_tasks);
        }

        // 检查终端状态
        if (data.stage === 'completed') {
          setState('success');
          closeSSE();
        } else if (data.stage === 'failed') {
          setState('error');
          setError(data.error || '安装失败');
          closeSSE();
        } else if (data.stage === 'cancelled') {
          setState('error');
          setError('安装已取消');
          closeSSE();
        }
      } catch {
        // 忽略解析错误
      }
    };

    es.addEventListener('done', (e) => {
      try {
        const { stage } = JSON.parse(e.data);
        if (stage === 'completed') {
          setState('success');
        } else {
          setState('error');
          setError(stage === 'failed' ? '安装失败' : '安装已取消');
        }
      } catch {
        setState('error');
      }
      closeSSE();
    });

    es.onerror = () => {
      // SSE 自动重连（由 retry 指令控制）
      // 如果连接彻底断开且任务已完成，关闭
      if (currentTaskRef.current !== taskId) {
        es.close();
      }
    };
  }, [closeSSE]);

  // 开始单游戏安装
  const startInstall = useCallback(async (gameUrl: string, installOrder?: string[]) => {
    setState('loading');
    setError(null);
    setProgress(null);
    setSubTasks([]);

    const response = await apiClient.startInstall({
      game_url: gameUrl,
      install_order: installOrder,
    });

    if (response.success && response.data) {
      startSSE(response.data.task_id);
    } else {
      setError(response.error || '启动安装失败');
      setState('error');
    }
  }, [startSSE]);

  // 开始批量安装
  const startBatchInstall = useCallback(async (gameNames: string[]) => {
    setState('loading');
    setError(null);
    setProgress(null);
    setSubTasks([]);

    const response = await apiClient.startBatchInstall(gameNames);

    if (response.success && response.data) {
      startSSE(response.data.task_id);
    } else {
      setError(response.error || '启动批量安装失败');
      setState('error');
    }
  }, [startSSE]);

  // 本地安装
  const localInstall = useCallback(async (folderPath: string) => {
    setState('loading');
    setError(null);
    setProgress(null);
    setSubTasks([]);

    const response = await apiClient.localInstall(folderPath);

    if (response.success && response.data) {
      startSSE(response.data.task_id);
    } else {
      setError(response.error || '启动本地安装失败');
      setState('error');
    }
  }, [startSSE]);

  // 重置状态
  const reset = useCallback(() => {
    closeSSE();
    currentTaskRef.current = null;
    setState('idle');
    setProgress(null);
    setSubTasks([]);
    setError(null);
  }, [closeSSE]);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      closeSSE();
    };
  }, [closeSSE]);

  return {
    state,
    progress,
    subTasks,
    error,
    startInstall,
    startBatchInstall,
    localInstall,
    reset,
    isLoading: state === 'loading',
    isCompleted: state === 'success',
    isFailed: state === 'error',
  };
}
