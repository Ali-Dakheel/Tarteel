import { laravelFetch } from '@/lib/server/laravel';

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const body = await req.text();
  const upstream = await laravelFetch(`/questions/${id}/attempt`, {
    method: 'POST',
    body,
  });
  const data = await upstream.json();
  return Response.json(data, { status: upstream.status });
}
