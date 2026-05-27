import { Download, Loader2 } from "lucide-react";

interface InstallButtonProps {
  onInstall: () => void;
  installing: boolean;
  disabled?: boolean;
}

export function InstallButton({
  onInstall,
  installing,
  disabled,
}: InstallButtonProps) {
  return (
    <div className="w-[200px]">
      <button
        onClick={onInstall}
        disabled={installing || disabled}
        className={`w-full h-11 rounded-lg flex items-center justify-center gap-2 text-white text-sm font-medium transition-all duration-150 ${
          installing || disabled
            ? "bg-accent/50 cursor-not-allowed"
            : "bg-accent hover:bg-accent/90 active:scale-[0.98]"
        }`}
      >
        {installing ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            <span>安装中...</span>
          </>
        ) : (
          <>
            <Download className="w-4 h-4" />
            <span>安装游戏</span>
          </>
        )}
      </button>
    </div>
  );
}
