// 搜索 Hook

import { useState, useCallback } from 'react';
import { apiClient } from '../api/client';
import type { GameItem, LoadingState } from '../types/api';

export function useSearch() {
  const [state, setState] = useState<LoadingState>('idle');
  const [results, setResults] = useState<GameItem[]>([]);
  const [error, setError] = useState<string | null>(null);

  const search = useCallback(async (keyword: string) => {
    if (!keyword.trim()) {
      setResults([]);
      setState('idle');
      return;
    }

    setState('loading');
    setError(null);

    const response = await apiClient.search(keyword);

    if (response.success && response.data) {
      setResults(response.data);
      setState(response.data.length > 0 ? 'success' : 'idle');
    } else {
      setError(response.error || '搜索失败');
      setState('error');
      setResults([]);
    }
  }, []);

  const clearResults = useCallback(() => {
    setResults([]);
    setState('idle');
    setError(null);
  }, []);

  return {
    state,
    results,
    error,
    search,
    clearResults,
    isLoading: state === 'loading',
    isEmpty: state === 'success' && results.length === 0,
    hasResults: state === 'success' && results.length > 0,
  };
}
