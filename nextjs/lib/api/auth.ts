import { parseApiError } from '@/lib/api/errors';
import type { User } from '@/types/api';

export type LoginPayload = { email: string; password: string };
export type RegisterPayload = { name: string; email: string; password: string; password_confirmation: string };
export type AuthResponse = { user: User; token: string };

export async function login(payload: LoginPayload): Promise<AuthResponse> {
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(await parseApiError(res, 'Login failed'));
  }
  return res.json() as Promise<AuthResponse>;
}

export async function register(payload: RegisterPayload): Promise<AuthResponse> {
  const res = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(await parseApiError(res, 'Registration failed'));
  }
  return res.json() as Promise<AuthResponse>;
}

export async function logout(): Promise<void> {
  await fetch('/api/auth/logout', { method: 'POST' });
}

export async function getMe(): Promise<User> {
  const res = await fetch('/api/auth/me');
  if (!res.ok) throw new Error('Unauthenticated');
  const body = await res.json() as { data: User };
  return body.data;
}
