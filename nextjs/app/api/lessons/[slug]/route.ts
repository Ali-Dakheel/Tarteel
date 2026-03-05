import { laravelFetch } from '@/lib/server/laravel';

export async function GET(
  _req: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params;
  const upstream = await laravelFetch(`/lessons/${slug}`);
  const data = await upstream.json();
  return Response.json(data, { status: upstream.status });
}
