import { Wifi, WifiOff, Crown } from "lucide-react";

interface StatusBarProps {
  connected: boolean;
  statusText: string;
  isVip: boolean;
  version: string;
}

export function StatusBar({ connected, statusText, isVip, version }: StatusBarProps) {
  return (
    <header className="h-10 bg-bg-card border-b border-divider flex items-center px-4 select-none">
      {/* Left: Switch status */}
      <div className="flex items-center gap-2 min-w-[160px]">
        {connected ? (
          <Wifi className="w-4 h-4 text-success" />
        ) : (
          <WifiOff className="w-4 h-4 text-error" />
        )}
        <span className={`text-sm ${connected ? "text-success" : "text-error"}`}>
          {connected ? "Switch 已连接" : "Switch 未连接"}
        </span>
      </div>

      {/* Center: status text */}
      <div className="flex-1 text-center">
        <span className="text-sm text-text-secondary">{statusText}</span>
      </div>

      {/* Right: VIP + version */}
      <div className="flex items-center gap-3 min-w-[160px] justify-end">
        {isVip ? (
          <div className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-gradient-to-r from-vip-gold to-yellow-600">
            <Crown className="w-3 h-3 text-bg" />
            <span className="text-xs font-medium text-bg">VIP</span>
          </div>
        ) : (
          <span className="text-xs text-text-secondary px-2 py-0.5 rounded-full border border-divider">
            基础版
          </span>
        )}
        <span className="text-xs text-text-secondary font-mono">v{version}</span>
      </div>
    </header>
  );
}
