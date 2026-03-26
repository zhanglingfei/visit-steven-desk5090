import api from './client';

export interface LoginResponse {
  token: string;
  username: string;
  requires_2fa: boolean;
}

export interface UserInfo {
  username: string;
  role: string;
  has_2fa: boolean;
  password_change_required?: boolean;
  password_change_reason?: string;
}

export interface Setup2FAResponse {
  secret: string;
  qr_code: string;
  backup_codes: string[];
}

export async function login(username: string, password: string, totpCode?: string): Promise<LoginResponse> {
  const response = await api.post('/auth/login', { username, password, totp_code: totpCode });
  return response.data;
}

export async function getMe(): Promise<UserInfo> {
  const response = await api.get('/auth/me');
  return response.data;
}

export async function setup2FA(username: string, password: string): Promise<Setup2FAResponse> {
  const response = await api.post('/auth/2fa/setup', { username, password });
  return response.data;
}

export async function verify2FA(username: string, password: string, totpCode: string): Promise<{ message: string; backup_codes: string[] }> {
  const response = await api.post('/auth/2fa/verify', { username, password, totp_code: totpCode });
  return response.data;
}

export async function disable2FA(username: string, password: string, totpCode: string): Promise<{ message: string }> {
  const response = await api.post('/auth/2fa/disable', { username, password, totp_code: totpCode });
  return response.data;
}

export async function changePassword(username: string, currentPassword: string, newPassword: string): Promise<{ message: string }> {
  const response = await api.post('/auth/change-password', { username, current_password: currentPassword, new_password: newPassword });
  return response.data;
}
