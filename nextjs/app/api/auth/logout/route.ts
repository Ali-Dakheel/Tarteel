import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { laravelFetch } from '@/lib/server/laravel';

export async function POST() {
  await laravelFetch('/auth/logout', { method: 'POST' });

  const res = NextResponse.json({ ok: true });
  const cookieStore = await cookies();
  const token = cookieStore.get('tarteel_token');
  if (token) {
    res.cookies.delete('tarteel_token');
  }
  return res;
}
