// 设备检测 Hook

import { useState, useCallback } from 'react';
import { apiClient } from '../api/client';
import type { SwitchDevice, LoadingState } from '../types/api';

export function useDevice() {
  const [state, setState] = useState<LoadingState>('idle');
  const [device, setDevice] = useState<SwitchDevice | null>(null);
  const [error, setError] = useState<string | null>(null);

  // 检测 Switch 设备
  const checkDevice = useCallback(async () => {
    setState('loading');
    setError(null);

    const response = await apiClient.checkSwitchDevice();

    if (response.success && response.data) {
      setDevice(response.data);
      setState('success');
    } else {
      setError(response.error || '设备检测失败');
      setState('error');
      setDevice(null);
    }
  }, []);

  // 重置状态
  const reset = useCallback(() => {
    setState('idle');
    setDevice(null);
    setError(null);
  }, []);

  return {
    state,
    device,
    error,
    checkDevice,
    reset,
    isLoading: state === 'loading',
    isConnected: device?.connected ?? false,
    isDbiMode: device?.dbi_mode ?? false,
    hasTfCard: device?.tf_card?.inserted ?? false,
  };
}
