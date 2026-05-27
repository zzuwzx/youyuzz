// MainPage 主页面

import React, { useState, useEffect, useCallback } from 'react';
import { 
  SearchBox, 
  GameList, 
  InstallProgress, 
  DeviceStatus,
  Loading, 
  Error, 
  Empty,
  Modal,
  LocalInstall
} from '../components';
import { useSearch, useInstall, useDevice } from '../hooks';
import type { GameItem } from '../types/api';

export default function MainPage() {
  const [selectedGame, setSelectedGame] = useState<GameItem | null>(null);
  const [showDeviceWarning, setShowDeviceWarning] = useState(false);
  const [showLocalInstall, setShowLocalInstall] = useState(false);
  
  const { 
    state: searchState, 
    results, 
    error: searchError, 
    search, 
    clearResults,
    isLoading: isSearching,
    isEmpty,
    hasResults
  } = useSearch();
  
  const { 
    state: installState, 
    progress, 
    error: installError, 
    startInstall, 
    localInstall,
    reset: resetInstall,
    isLoading: isInstalling,
    isCompleted,
    isFailed
  } = useInstall();
  
  const { 
    state: deviceState, 
    device, 
    error: deviceError, 
    checkDevice,
    isLoading: isCheckingDevice
  } = useDevice();

  // 启动时检测设备
  useEffect(() => {
    checkDevice();
  }, [checkDevice]);

  // 设备未连接时显示警告
  useEffect(() => {
    if (deviceState === 'success' && device && !device.connected) {
      setShowDeviceWarning(true);
    }
  }, [deviceState, device]);

  // 选择游戏
  const handleSelectGame = useCallback((game: GameItem) => {
    setSelectedGame(game);
  }, []);

  // 开始安装
  const handleStartInstall = useCallback(() => {
    if (selectedGame) {
      startInstall(selectedGame.source_url);
    }
  }, [selectedGame, startInstall]);

  // 本地安装
  const handleLocalInstall = useCallback((folderPath: string) => {
    localInstall(folderPath);
    setShowLocalInstall(false);
  }, [localInstall]);

  // 重试安装
  const handleRetryInstall = useCallback(() => {
    if (selectedGame) {
      startInstall(selectedGame.source_url);
    }
  }, [selectedGame, startInstall]);

  return (
    <div className="flex flex-col h-screen">
      {/* 状态栏 */}
      <header className="h-10 bg-bg-card border-b border-divider flex items-center px-4 justify-between">
        <span className="text-text-secondary text-sm">楸块儊浠斾粩 v0.2.0</span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowLocalInstall(true)}
            className="px-3 py-1 bg-accent-secondary hover:bg-accent text-white rounded text-sm transition-colors"
          >
            本地安装
          </button>
          <button
            onClick={checkDevice}
            disabled={isCheckingDevice}
            className="px-3 py-1 bg-bg-card border border-divider hover:border-accent text-text-primary rounded text-sm transition-colors"
          >
            {isCheckingDevice ? '检测中...' : '检测设备'}
          </button>
        </div>
      </header>

      {/* 主内容 */}
      <main className="flex-1 flex overflow-hidden">
        {/* 左侧：搜索和游戏列表 */}
        <div className="flex-1 flex flex-col p-6 space-y-6 overflow-hidden">
          {/* 搜索框 */}
          <SearchBox onSearch={search} isLoading={isSearching} />
          
          {/* 搜索结果 */}
          <div className="flex-1 overflow-y-auto">
            {isSearching && (
              <Loading message="搜索中..." />
            )}
            
            {searchState === 'error' && searchError && (
              <Error message={searchError} onRetry={() => search(selectedGame?.title || '')} />
            )}
            
            {isEmpty && (
              <Empty message="未找到相关游戏" />
            )}
            
            {hasResults && (
              <GameList 
                games={results} 
                onSelect={handleSelectGame}
                selectedUrl={selectedGame?.source_url}
              />
            )}
            
            {searchState === 'idle' && !isSearching && (
              <Empty message="输入关键词搜索游戏" />
            )}
          </div>
        </div>

        {/* 右侧：设备状态和安装 */}
        <div className="w-96 border-l border-divider p-6 space-y-6 overflow-y-auto">
          {/* 设备状态 */}
          <DeviceStatus 
            device={device}
            isLoading={isCheckingDevice}
            onRefresh={checkDevice}
          />

          {/* 选中的游戏信息 */}
          {selectedGame && !isInstalling && !isCompleted && !isFailed && (
            <div className="p-6 bg-bg-card rounded-lg border border-divider">
              <h3 className="text-lg font-medium text-text-primary mb-4">已选择游戏</h3>
              <div className="space-y-2 mb-4">
                <div>
                  <span className="text-text-secondary text-sm">游戏名称:</span>
                  <p className="text-text-primary">{selectedGame.title}</p>
                </div>
                {selectedGame.version && (
                  <div>
                    <span className="text-text-secondary text-sm">版本:</span>
                    <p className="text-text-primary">{selectedGame.version}</p>
                  </div>
                )}
                {selectedGame.size && (
                  <div>
                    <span className="text-text-secondary text-sm">大小:</span>
                    <p className="text-text-primary">{selectedGame.size}</p>
                  </div>
                )}
              </div>
              <button
                onClick={handleStartInstall}
                disabled={!device?.connected}
                className="w-full py-3 bg-accent hover:bg-accent/80 disabled:bg-divider disabled:text-text-secondary text-white rounded-lg transition-colors font-medium"
              >
                {!device?.connected ? '请先连接设备' : '开始安装'}
              </button>
            </div>
          )}

          {/* 安装进度 */}
          {progress && (
            <InstallProgress 
              progress={progress}
              onCancel={resetInstall}
            />
          )}

          {/* 安装完成 */}
          {isCompleted && (
            <div className="p-6 bg-success/10 border border-success/30 rounded-lg">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-success/20 flex items-center justify-center">
                  <svg className="w-6 h-6 text-success" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-medium text-text-primary">安装完成</h3>
                  <p className="text-sm text-text-secondary">游戏已成功安装到设备</p>
                </div>
              </div>
              <button
                onClick={resetInstall}
                className="w-full py-2 bg-accent-secondary hover:bg-accent text-white rounded-lg transition-colors"
              >
                继续安装其他游戏
              </button>
            </div>
          )}

          {/* 安装失败 */}
          {isFailed && (
            <div className="p-6 bg-error/10 border border-error/30 rounded-lg">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-full bg-error/20 flex items-center justify-center">
                  <svg className="w-6 h-6 text-error" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-medium text-text-primary">安装失败</h3>
                  <p className="text-sm text-text-secondary">{installError || '未知错误'}</p>
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={handleRetryInstall}
                  className="flex-1 py-2 bg-accent hover:bg-accent/80 text-white rounded-lg transition-colors"
                >
                  重试
                </button>
                <button
                  onClick={resetInstall}
                  className="flex-1 py-2 bg-accent-secondary hover:bg-accent text-white rounded-lg transition-colors"
                >
                  取消
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* 设备未连接警告弹窗 */}
      <Modal
        isOpen={showDeviceWarning}
        onClose={() => setShowDeviceWarning(false)}
        title="设备未连接"
      >
        <div className="space-y-4">
          <div className="flex items-center gap-3 p-4 bg-warning/10 border border-warning/30 rounded-lg">
            <svg className="w-8 h-8 text-warning flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div>
              <p className="text-text-primary font-medium">未检测到 Switch 设备</p>
              <p className="text-sm text-text-secondary mt-1">
                请确保 Switch 已通过 USB 连接到电脑，并且已开启 DBI 模式。
              </p>
            </div>
          </div>
          
          <div className="space-y-2 text-sm text-text-secondary">
            <p className="font-medium text-text-primary">连接步骤:</p>
            <ol className="list-decimal list-inside space-y-1">
              <li>在 Switch 上打开 DBI 应用</li>
              <li>选择 "MTP responder" 模式</li>
              <li>使用 USB 数据线连接 Switch 和电脑</li>
              <li>点击下方 "重新检测" 按钮</li>
            </ol>
          </div>

          <div className="flex gap-2 pt-4">
            <button
              onClick={() => {
                checkDevice();
                setShowDeviceWarning(false);
              }}
              className="flex-1 py-2 bg-accent hover:bg-accent/80 text-white rounded-lg transition-colors"
            >
              重新检测
            </button>
            <button
              onClick={() => setShowDeviceWarning(false)}
              className="flex-1 py-2 bg-accent-secondary hover:bg-accent text-white rounded-lg transition-colors"
            >
              稍后再说
            </button>
          </div>
        </div>
      </Modal>

      {/* 本地安装弹窗 */}
      <Modal
        isOpen={showLocalInstall}
        onClose={() => setShowLocalInstall(false)}
        title="本地离线安装"
      >
        <LocalInstall 
          onInstall={handleLocalInstall}
          isLoading={isInstalling}
        />
      </Modal>
    </div>
  );
}
