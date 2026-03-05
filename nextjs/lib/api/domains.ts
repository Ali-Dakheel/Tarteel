import type { Domain, Lesson } from '@/types/api';

export async function getDomains(): Promise<Domain[]> {
  const res = await fetch('/api/domains');
  if (!res.ok) throw new Error('Failed to load domains');
  const body = await res.json();
  return (body as { data: Domain[] }).data;
}

export async function getDomainLessons(slug: string): Promise<Lesson[]> {
  const res = await fetch(`/api/domains/${slug}/lessons`);
  if (!res.ok) throw new Error('Failed to load lessons');
  const body = await res.json();
  return (body as { data: Lesson[] }).data;
}
