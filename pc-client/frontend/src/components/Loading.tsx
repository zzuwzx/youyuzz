// Loading 组件

import React from 'react';

interface LoadingProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
}

export function Loading({ message = '加载中...', size = 'md' }: LoadingProps) {
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  };

  return (
    <div className="flex flex-col items-center justify-center p-8 gap-4">
      <div className={`${sizeClasses[size]} border-4 border-accent-secondary border-t-accent rounded-full animate-spin`} />
      <p className="text-text-secondary text-sm">{message}</p>
    </div>
  );
}
