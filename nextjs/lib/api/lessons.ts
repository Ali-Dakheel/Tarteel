import type { Lesson } from '@/types/api';

export async function getLesson(slug: string): Promise<Lesson> {
  const res = await fetch(`/api/lessons/${slug}`);
  if (!res.ok) {
    if (res.status === 403) throw new Error('pro_required');
    throw new Error('Failed to load lesson');
  }
  const body = await res.json();
  return (body as { data: Lesson }).data;
}

export async function markProgress(slug: string, timeSpentSeconds: number): Promise<void> {
  await fetch(`/api/lessons/${slug}/progress`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ time_spent_seconds: timeSpentSeconds }),
  });
}
