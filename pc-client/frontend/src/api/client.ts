// API 通信层封装

import type { 
  GameItem, 
  GameDetail, 
  InstallRequest, 
  BatchInstallRequest,
  InstallResponse, 
  InstallProgress,
  SubTaskProgress,
  SwitchDevice,
  AppSettings,
  ApiResponse 
} from '../types/api';
import type { AuthStatus } from '../types/auth';

type ActivateLicenseResponse = { success: boolean; message?: string; license_key?: string };

const BASE_URL = '/api';

class ApiClient {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    try {
      const response = await fetch(`${BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options.headers,
        },
        ...options,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        return {
          success: false,
          error: errorData.message || errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        };
      }

      const data = await response.json();
      return {
        success: true,
        data,
      };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : '网络请求失败',
      };
    }
  }

  // 搜索接口
  async search(keyword: string): Promise<ApiResponse<GameItem[]>> {
    return this.request<GameItem[]>(`/search?keyword=${encodeURIComponent(keyword)}`);
  }

  // 游戏详情
  async getGameDetail(url: string): Promise<ApiResponse<GameDetail>> {
    return this.request<GameDetail>(`/game/detail?url=${encodeURIComponent(url)}`);
  }

  // 开始安装
  async startInstall(request: InstallRequest): Promise<ApiResponse<InstallResponse>> {
    return this.request<InstallResponse>('/install', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // 获取安装进度
  async getInstallProgress(taskId: string): Promise<ApiResponse<InstallProgress>> {
    return this.request<InstallProgress>(`/install/${taskId}/progress`);
  }

  // 批量安装（VIP）
  async startBatchInstall(gameNames: string[]): Promise<ApiResponse<InstallResponse>> {
    return this.request<InstallResponse>('/install/batch', {
      method: 'POST',
      body: JSON.stringify({ game_names: gameNames }),
    });
  }

  // 获取批量子任务进度
  async getSubTasks(taskId: string): Promise<ApiResponse<{ task_id: string; sub_tasks: SubTaskProgress[] }>> {
    return this.request<{ task_id: string; sub_tasks: SubTaskProgress[] }>(`/install/${taskId}/sub_tasks`);
  }

  // 本地安装
  async localInstall(folderPath: string): Promise<ApiResponse<InstallResponse>> {
    return this.request<InstallResponse>('/install/local', {
      method: 'POST',
      body: JSON.stringify({ folder_path: folderPath }),
    });
  }

  // 检测 Switch 设备
  async checkSwitchDevice(): Promise<ApiResponse<SwitchDevice>> {
    return this.request<SwitchDevice>('/device/switch');
  }

  // 检测 TF 卡状态
  async checkTfCard(): Promise<ApiResponse<{ inserted: boolean }>> {
    return this.request<{ inserted: boolean }>('/device/tfcard');
  }

  // 获取设置
  async getSettings(): Promise<ApiResponse<AppSettings>> {
    return this.request<AppSettings>('/settings');
  }

  // 保存设置
  async saveSettings(settings: Partial<AppSettings>): Promise<ApiResponse<void>> {
    return this.request<void>('/settings', {
      method: 'PUT',
      body: JSON.stringify(settings),
    });
  }

  // 更新单个设置项
  async updateSetting(key: string, value: string): Promise<ApiResponse<void>> {
    return this.request<void>('/settings', {
      method: 'PUT',
      body: JSON.stringify({ key, value }),
    });
  }

  // 获取授权状态
  async getAuthStatus(): Promise<ApiResponse<AuthStatus>> {
    return this.request<AuthStatus>('/auth/status');
  }

  // 激活授权码
  async activateLicense(code: string): Promise<ApiResponse<ActivateLicenseResponse>> {
    return this.request<ActivateLicenseResponse>('/auth/activate', {
      method: 'POST',
      body: JSON.stringify({ code }),
    });
  }

  // 健康检查
  async healthCheck(): Promise<ApiResponse<{ status: string }>> {
    return this.request<{ status: string }>('/health');
  }
}

export const apiClient = new ApiClient();
