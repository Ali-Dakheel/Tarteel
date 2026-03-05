import { laravelFetch } from '@/lib/server/laravel';

export async function GET() {
  const upstream = await laravelFetch('/streaks');
  const data = await upstream.json();
  return Response.json(data, { status: upstream.status });
}
