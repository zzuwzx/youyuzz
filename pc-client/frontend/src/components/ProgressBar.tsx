import type { InstallProgress } from "../types/api";

interface ProgressBarProps {
  progress: InstallProgress;
}

export function ProgressBar({ progress }: ProgressBarProps) {
  return (
    <div className="w-full space-y-2">
      {/* Bar */}
      <div className="w-full h-1.5 bg-divider rounded-full overflow-hidden">
        <div
          className="h-full bg-accent rounded-full transition-all duration-300 ease-out"
          style={{ width: `${Math.min(100, Math.max(0, progress.progress))}%` }}
        />
      </div>

      {/* Details */}
      <div className="flex items-center justify-between text-xs text-text-secondary">
        <span className="truncate max-w-[50%]">{progress.current_file || '准备中...'}</span>
        <span>
          {progress.total_files > 0 ? `${progress.current_file} / ${progress.total_files}` : '-'}
        </span>
      </div>

      {/* Speed + ETA */}
      {(progress.speed || progress.eta) && (
        <div className="flex items-center gap-4 text-xs text-text-secondary">
          {progress.speed && <span>速度: {progress.speed}</span>}
          {progress.eta && <span>剩余: {progress.eta}</span>}
        </div>
      )}

      {/* Error */}
      {progress.status === 'failed' && progress.error && (
        <div className="p-2 bg-error/10 border border-error/30 rounded text-xs text-error">
          {progress.error}
        </div>
      )}
    </div>
  );
}
