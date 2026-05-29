// 授权状态类型

export interface AuthStatus {
  is_vip: boolean;
  license_key?: string | null;
  expires_at?: string | null;
}
