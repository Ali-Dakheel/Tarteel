'use client';

import { useTranslations } from 'next-intl';
import { Link } from '@/i18n/navigation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ArrowRight } from 'lucide-react';
import type { Domain } from '@/types/api';

type Props = { domain: Domain };

// Domain icon map
const DOMAIN_EMOJI: Record<string, string> = {
  people: '👥',
  process: '⚙️',
  'business-environment': '🏢',
};

export function DomainCard({ domain }: Props) {
  const t = useTranslations('domains');

  return (
    <Link href={`/learn/${domain.slug}`}>
      <Card className="h-full cursor-pointer transition-shadow hover:shadow-md">
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="text-3xl">{DOMAIN_EMOJI[domain.slug] ?? '📚'}</div>
            <Badge variant="outline">
              {domain.lesson_count ?? 0} {t('lessons')}
            </Badge>
          </div>
          <CardTitle className="mt-2">{domain.name}</CardTitle>
          <CardDescription className="line-clamp-2">{domain.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>{t('start')}</span>
            <ArrowRight className="h-4 w-4 rtl:rotate-180" />
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
