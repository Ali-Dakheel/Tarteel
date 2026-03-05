import { NextResponse } from 'next/server';

const LARAVEL_URL = process.env.LARAVEL_URL ?? 'http://localhost:8000';

export async function POST(req: Request) {
  const body = await req.json();
  const upstream = await fetch(`${LARAVEL_URL}/api/v1/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  const data = await upstream.json();
  if (!upstream.ok) {
    return NextResponse.json(data, { status: upstream.status });
  }

  const { token, user } = (data as { data: { token: string; user: unknown } }).data;

  const res = NextResponse.json({ user });
  res.cookies.set('tarteel_token', token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    maxAge: 60 * 60 * 24 * 30, // 30 days
  });
  return res;
}
