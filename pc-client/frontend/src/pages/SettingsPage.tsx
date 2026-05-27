import { useState } from "react";
import { ArrowLeft, Cloud, Bell, Settings } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface SettingItem {
  label: string;
  type: "input" | "toggle";
  value: string | boolean;
  placeholder?: string;
}

function SettingRow({
  item,
  onChange,
}: {
  item: SettingItem;
  onChange: (value: string | boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-divider last:border-0">
      <span className="text-sm text-text-primary">{item.label}</span>
      {item.type === "input" ? (
        <input
          type="text"
          value={item.value as string}
          onChange={(e) => onChange(e.target.value)}
          placeholder={item.placeholder}
          className="w-64 h-8 px-3 bg-bg border border-divider rounded text-sm text-text-primary placeholder:text-text-secondary outline-none focus:border-accent transition-colors duration-150"
        />
      ) : (
        <button
          onClick={() => onChange(!item.value)}
          className={`w-10 h-5 rounded-full transition-colors duration-150 ${
            item.value ? "bg-accent" : "bg-divider"
          }`}
        >
          <div
            className={`w-4 h-4 rounded-full bg-white shadow transition-transform duration-150 ${
              item.value ? "translate-x-5" : "translate-x-0.5"
            }`}
          />
        </button>
      )}
    </div>
  );
}

export default function SettingsPage() {
  const navigate = useNavigate();

  // Cloud settings
  const [cookie, setCookie] = useState("");
  const [quarkCookie, setQuarkCookie] = useState("");

  // Notification settings
  const [pushdeerKey, setPushdeerKey] = useState("");
  const [notifyOnComplete, setNotifyOnComplete] = useState(true);
  const [notifyOnError, setNotifyOnError] = useState(true);

  // General settings
  const [autoDetect, setAutoDetect] = useState(true);
  const [darkMode, setDarkMode] = useState(true);
  const [cachePath, setCachePath] = useState("");

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
        <h1 className="text-lg text-text-primary font-medium">设置</h1>
      </div>

      <div className="px-8 py-6 space-y-6 max-w-2xl mx-auto">
        {/* 网盘设置 */}
        <div className="bg-bg-card border border-divider rounded-lg p-4">
          <div className="flex items-center gap-2 mb-4">
            <Cloud className="w-4 h-4 text-accent" />
            <h2 className="text-sm text-text-primary font-medium">网盘设置</h2>
          </div>
          <SettingRow
            item={{ label: "百度网盘 Cookie", type: "input", value: cookie, placeholder: "粘贴 BDUSS..." }}
            onChange={(v) => setCookie(v as string)}
          />
          <SettingRow
            item={{ label: "夸克网盘 Cookie", type: "input", value: quarkCookie, placeholder: "粘贴 Cookie..." }}
            onChange={(v) => setQuarkCookie(v as string)}
          />
        </div>

        {/* 通知设置 */}
        <div className="bg-bg-card border border-divider rounded-lg p-4">
          <div className="flex items-center gap-2 mb-4">
            <Bell className="w-4 h-4 text-accent" />
            <h2 className="text-sm text-text-primary font-medium">通知设置</h2>
          </div>
          <SettingRow
            item={{ label: "PushDeer Key", type: "input", value: pushdeerKey, placeholder: "输入 PushDeer Key..." }}
            onChange={(v) => setPushdeerKey(v as string)}
          />
          <SettingRow
            item={{ label: "安装完成通知", type: "toggle", value: notifyOnComplete }}
            onChange={(v) => setNotifyOnComplete(v as boolean)}
          />
          <SettingRow
            item={{ label: "错误通知", type: "toggle", value: notifyOnError }}
            onChange={(v) => setNotifyOnError(v as boolean)}
          />
        </div>

        {/* 通用设置 */}
        <div className="bg-bg-card border border-divider rounded-lg p-4">
          <div className="flex items-center gap-2 mb-4">
            <Settings className="w-4 h-4 text-accent" />
            <h2 className="text-sm text-text-primary font-medium">通用设置</h2>
          </div>
          <SettingRow
            item={{ label: "自动检测设备", type: "toggle", value: autoDetect }}
            onChange={(v) => setAutoDetect(v as boolean)}
          />
          <SettingRow
            item={{ label: "深色模式", type: "toggle", value: darkMode }}
            onChange={(v) => setDarkMode(v as boolean)}
          />
          <SettingRow
            item={{ label: "缓存路径", type: "input", value: cachePath, placeholder: "默认: C:\\Cache..." }}
            onChange={(v) => setCachePath(v as string)}
          />
        </div>
      </div>
    </div>
  );
}
