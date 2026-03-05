import 'server-only';
import { cookies } from 'next/headers';

const LARAVEL_URL = process.env.LARAVEL_URL ?? 'http://localhost:8000';

/** Server-side fetch helper that attaches the auth token from the httpOnly cookie. */
export async function laravelFetch(
  path: string,
  init: RequestInit = {},
): Promise<Response> {
  const token = (await cookies()).get('tarteel_token')?.value;

  return fetch(`${LARAVEL_URL}/api/v1${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers as Record<string, string>),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
}
