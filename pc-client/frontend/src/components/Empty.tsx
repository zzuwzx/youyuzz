// Empty 组件

import React from 'react';

interface EmptyProps {
  message?: string;
  icon?: React.ReactNode;
}

export function Empty({ message = '暂无数据', icon }: EmptyProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 gap-4">
      <div className="w-16 h-16 rounded-full bg-bg-card flex items-center justify-center">
        {icon || (
          <svg className="w-8 h-8 text-text-secondary" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
          </svg>
        )}
      </div>
      <p className="text-text-secondary text-center">{message}</p>
    </div>
  );
}
