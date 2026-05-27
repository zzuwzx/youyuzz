import { useState } from "react";
import { ArrowLeft, Crown, Check, X, Sparkles } from "lucide-react";
import { useNavigate } from "react-router-dom";

const BASIC_FEATURES = [
  "单游戏搜索",
  "单游戏安装",
  "本地离线安装",
  "基础进度显示",
  "设备状态检测",
];

const VIP_FEATURES = [
  "批量安装队列",
  "游戏版本自动更新检测",
  "实时进度 + 速度 + ETA",
  "PushDeer 消息推送",
  "大气层一键升级",
  "多 Switch 并行安装",
  "百度/阿里网盘加速",
];

export default function VIPPage() {
  const navigate = useNavigate();
  const [code, setCode] = useState("");

  const handleActivate = () => {
    // Placeholder: no real activation logic
    alert("激活功能待接入后端 API");
  };

  return (
    <div className="min-h-screen bg-bg">
      {/* Header */}
      <div className="flex items-center gap-3 px-8 py-4 border-b border-divider">
        <button
          onClick={() => navigate("/")}
          className="p-1.5 rounded-lg hover:bg-bg-card transition-colors duration-150"
        >
          <ArrowLeft className="w-5 h-5 text-text-secondary" />
        </button>
        <h1 className="text-lg text-text-primary font-medium">升级 VIP</h1>
      </div>

      <div className="px-8 py-8 max-w-3xl mx-auto space-y-8">
        {/* Title */}
        <div className="text-center space-y-2">
          <div className="flex items-center justify-center gap-2">
            <Sparkles className="w-6 h-6 text-vip-gold" />
            <h2 className="text-xl text-text-primary font-medium">解锁进阶功能</h2>
          </div>
          <p className="text-sm text-text-secondary">
            VIP 解锁全部高级功能，提升安装效率
          </p>
        </div>

        {/* Comparison cards */}
        <div className="grid grid-cols-2 gap-4">
          {/* Basic */}
          <div className="bg-bg-card border border-divider rounded-lg p-5 space-y-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-divider flex items-center justify-center">
                <span className="text-xs text-text-secondary">B</span>
              </div>
              <span className="text-sm text-text-primary font-medium">基础版</span>
              <span className="text-xs text-text-secondary ml-auto">免费</span>
            </div>

            <ul className="space-y-2.5">
              {BASIC_FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm text-text-secondary">
                  <Check className="w-4 h-4 text-success flex-shrink-0" />
                  <span>{f}</span>
                </li>
              ))}
              {VIP_FEATURES.slice(0, 3).map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm text-text-secondary/40">
                  <X className="w-4 h-4 flex-shrink-0" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </div>

          {/* VIP */}
          <div className="bg-bg-card border border-vip-gold/30 rounded-lg p-5 space-y-4 relative overflow-hidden">
            {/* Gold accent */}
            <div className="absolute top-0 right-0 w-20 h-20 bg-vip-gold/5 rounded-bl-full" />

            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-full bg-gradient-to-br from-vip-gold to-yellow-600 flex items-center justify-center">
                <Crown className="w-4 h-4 text-bg" />
              </div>
              <span className="text-sm text-text-primary font-medium">VIP 版</span>
              <span className="text-xs text-vip-gold ml-auto">全部功能</span>
            </div>

            <ul className="space-y-2.5">
              {BASIC_FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm text-text-secondary">
                  <Check className="w-4 h-4 text-success flex-shrink-0" />
                  <span>{f}</span>
                </li>
              ))}
              {VIP_FEATURES.map((f) => (
                <li key={f} className="flex items-center gap-2 text-sm text-vip-gold">
                  <Check className="w-4 h-4 flex-shrink-0" />
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Activation code */}
        <div className="bg-bg-card border border-divider rounded-lg p-5 space-y-4">
          <h3 className="text-sm text-text-primary font-medium">输入激活码</h3>

          <div className="flex gap-3">
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="输入 16 位激活码..."
              className="flex-1 h-10 px-4 bg-bg border border-divider rounded-lg text-sm text-text-primary placeholder:text-text-secondary outline-none focus:border-accent transition-colors duration-150 font-mono"
            />
            <button
              onClick={handleActivate}
              disabled={!code.trim()}
              className={`h-10 px-6 rounded-lg text-sm font-medium transition-all duration-150 ${
                code.trim()
                  ? "bg-accent text-white hover:bg-accent/90 active:scale-[0.98]"
                  : "bg-divider text-text-secondary cursor-not-allowed"
              }`}
            >
              激活
            </button>
          </div>

          <p className="text-xs text-text-secondary">
            兑换码可闲鱼搜索「鱿鱼仔仔」
          </p>
        </div>
      </div>
    </div>
  );
}
