// 授权 Hook

import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { AuthStatus } from '../types/auth';
import { apiClient } from '../api/client';
import type { LoadingState } from '../types/api';

interface AuthContextValue {
  state: LoadingState;
  isVip: boolean;
  licenseKey: string | null;
  expiresAt: string | null;
  error: string | null;
  isLoading: boolean;
  activate: (code: string) => Promise<boolean>;
  checkStatus: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<LoadingState>('idle');
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const checkStatus = useCallback(async () => {
    setState('loading');
    setError(null);

    const response = await apiClient.getAuthStatus();

    if (response.success && response.data) {
      setStatus(response.data);
      setState('success');
    } else {
      setError(response.error || '获取授权状态失败');
      setState('error');
    }
  }, []);

  const activate = useCallback(async (code: string) => {
    setState('loading');
    setError(null);

    const response = await apiClient.activateLicense(code);

    if (!response.success || !response.data) {
      setError(response.error || '激活失败，请稍后重试');
      setState('error');
      return false;
    }

    if (!response.data.success) {
      setError(response.data.message || '激活失败');
      setState('error');
      return false;
    }

    await checkStatus();
    return true;
  }, [checkStatus]);

  useEffect(() => {
    checkStatus();
  }, [checkStatus]);

  const value: AuthContextValue = {
    state,
    isVip: Boolean(status?.is_vip),
    licenseKey: status?.license_key ?? null,
    expiresAt: status?.expires_at ?? null,
    error,
    isLoading: state === 'loading',
    activate,
    checkStatus,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth 必须在 AuthProvider 内使用');
  }
  return ctx;
}
