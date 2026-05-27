// Error 组件

import React from 'react';

interface ErrorProps {
  message: string;
  onRetry?: () => void;
}

export function Error({ message, onRetry }: ErrorProps) {
  return (
    <div className="flex flex-col items-center justify-center p-8 gap-4">
      <div className="w-16 h-16 rounded-full bg-error/20 flex items-center justify-center">
        <svg className="w-8 h-8 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </div>
      <p className="text-error text-center">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-2 bg-accent-secondary hover:bg-accent-secondary/80 text-text-primary rounded-lg transition-colors"
        >
          重试
        </button>
      )}
    </div>
  );
}
