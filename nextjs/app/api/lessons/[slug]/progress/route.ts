import { laravelFetch } from '@/lib/server/laravel';

export async function POST(
  req: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params;
  const body = await req.text();
  const upstream = await laravelFetch(`/lessons/${slug}/progress`, {
    method: 'POST',
    body,
  });
  const data = await upstream.json();
  return Response.json(data, { status: upstream.status });
}
