// LocalInstall 组件

import React, { useState, useCallback } from 'react';

interface LocalInstallProps {
  onInstall: (folderPath: string) => void;
  isLoading?: boolean;
}

export function LocalInstall({ onInstall, isLoading = false }: LocalInstallProps) {
  const [folderPath, setFolderPath] = useState('');

  const handleSelectFolder = useCallback(async () => {
    // 在 Electron 环境中使用文件夹选择对话框
    // 这里暂时使用 input 模拟
    const input = document.createElement('input');
    input.type = 'file';
    input.webkitdirectory = true;
    input.multiple = false;
    
    input.onchange = (e) => {
      const files = (e.target as HTMLInputElement).files;
      if (files && files.length > 0) {
        // 获取第一个文件的路径（在 Electron 中可以获取完整路径）
        const path = files[0].webkitRelativePath.split('/')[0];
        setFolderPath(path);
      }
    };
    
    input.click();
  }, []);

  const handleInstall = useCallback(() => {
    if (folderPath.trim() && !isLoading) {
      onInstall(folderPath.trim());
    }
  }, [folderPath, isLoading, onInstall]);

  return (
    <div className="p-6 bg-bg-card rounded-lg border border-divider">
      <h3 className="text-lg font-medium text-text-primary mb-4">本地离线安装</h3>
      
      <div className="space-y-4">
        <div>
          <label className="block text-sm text-text-secondary mb-2">选择游戏文件夹</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              placeholder="输入或选择游戏文件夹路径"
              className="flex-1 px-4 py-2 bg-bg border border-divider rounded-lg text-text-primary placeholder-text-secondary focus:outline-none focus:border-accent transition-colors"
              disabled={isLoading}
            />
            <button
              onClick={handleSelectFolder}
              disabled={isLoading}
              className="px-4 py-2 bg-accent-secondary hover:bg-accent disabled:bg-divider disabled:text-text-secondary text-white rounded-lg transition-colors"
            >
              选择
            </button>
          </div>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleInstall}
            disabled={!folderPath.trim() || isLoading}
            className="px-6 py-2 bg-accent hover:bg-accent/80 disabled:bg-divider disabled:text-text-secondary text-white rounded-lg transition-colors font-medium"
          >
            {isLoading ? '安装中...' : '开始安装'}
          </button>
        </div>
      </div>

      <div className="mt-4 p-3 bg-accent-secondary/20 border border-accent-secondary/30 rounded-lg">
        <p className="text-sm text-text-secondary">
          <strong>提示:</strong> 请选择包含游戏文件的文件夹，支持 NSP、XCI 格式的游戏文件。
        </p>
      </div>
    </div>
  );
}
