// API 响应类型定义

export interface GameItem {
  title: string;
  version: string;
  size: string;
  source_url: string;
}

export interface GameDetail {
  title: string;
  body_url: string;
  update_url: string;
  dlc_url: string;
  cheat_url: string;
}

export interface InstallRequest {
  game_url: string;
  install_order?: string[];
}

export interface BatchInstallRequest {
  game_names: string[];
}

export interface InstallResponse {
  task_id: string;
}

export interface SubTaskProgress {
  task_id: string;
  game_name: string;
  stage: string;
  percent: number;
  error?: string;
}

export interface InstallProgress {
  task_id: string;
  stage: string;
  percent: number;
  current_file: string;
  total_files: number;
  completed_files: number;
  speed: string;
  eta: string;
  error?: string;
  sub_tasks?: SubTaskProgress[];
}

export interface SwitchDevice {
  connected: boolean;
  device_name: string;
  dbi_mode: boolean;
  tf_card: {
    inserted: boolean;
    total_space: number;
    free_space: number;
  };
}

export interface AppSettings {
  download_path: string;
  auto_install: boolean;
  notification_enabled: boolean;
  pushdeer_key: string;
  language: string;
  theme: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export type LoadingState = 'idle' | 'loading' | 'success' | 'error';
