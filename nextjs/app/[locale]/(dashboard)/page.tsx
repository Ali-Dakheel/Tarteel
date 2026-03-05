'use client';

import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { getDomains } from '@/lib/api/domains';
import { queryKeys } from '@/lib/queryKeys';
import { DomainCard } from '@/components/domains/DomainCard';
import type { Domain } from '@/types/api';

export default function HomePage() {
  const t = useTranslations('domains');

  const { data: domains, isPending, error } = useQuery<Domain[]>({
    queryKey: queryKeys.domains.all(),
    queryFn: getDomains,
    staleTime: 5 * 60 * 1000,
  });

  if (isPending) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-40 animate-pulse rounded-xl bg-muted" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center text-destructive py-12">
        <p>{t('title')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">{t('title')}</h1>
        <p className="text-muted-foreground mt-1">{t('subtitle')}</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {domains?.map((domain) => (
          <DomainCard key={domain.id} domain={domain} />
        ))}
      </div>
    </div>
  );
}
