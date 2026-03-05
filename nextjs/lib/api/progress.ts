import type { Progress, Streak } from '@/types/api';

export async function getProgress(): Promise<Progress> {
  const res = await fetch('/api/progress');
  if (!res.ok) throw new Error('Failed to load progress');
  const body = await res.json();
  return (body as { data: Progress }).data;
}

export async function getStreak(): Promise<Streak> {
  const res = await fetch('/api/streaks');
  if (!res.ok) throw new Error('Failed to load streak');
  const body = await res.json();
  return (body as { data: Streak }).data;
}
