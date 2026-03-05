import { cookies } from 'next/headers';

const LARAVEL_URL = process.env.LARAVEL_URL ?? 'http://localhost:8000';

export async function POST(req: Request) {
  const token = (await cookies()).get('tarteel_token')?.value;
  if (!token) {
    return new Response(JSON.stringify({ message: 'Unauthenticated.' }), { status: 401 });
  }

  const body = await req.text();

  const upstream = await fetch(`${LARAVEL_URL}/api/v1/tutor/explain`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body,
  });

  if (!upstream.ok || !upstream.body) {
    const errText = await upstream.text().catch(() => 'AI service unavailable');
    return new Response(errText, {
      status: upstream.status,
      headers: { 'Content-Type': upstream.headers.get('Content-Type') ?? 'application/json' },
    });
  }

  // Stream the SSE response directly to the client
  return new Response(upstream.body, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'X-Accel-Buffering': 'no',
    },
  });
}
