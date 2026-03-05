'use client';

import { useTranslations } from 'next-intl';
import { useQuery } from '@tanstack/react-query';
import { getMe } from '@/lib/api/auth';
import { queryKeys } from '@/lib/queryKeys';
import { Badge } from '@/components/ui/badge';
import type { User } from '@/types/api';

export function TopBar() {
  const tCommon = useTranslations('common');

  const { data: user } = useQuery<User>({
    queryKey: queryKeys.user.me(),
    queryFn: getMe,
    staleTime: 5 * 60 * 1000,
  });

  return (
    <header className="flex h-16 items-center justify-between border-b bg-card px-6">
      <div className="md:hidden">
        <span className="text-lg font-bold text-primary">تَرتيل</span>
      </div>
      <div className="flex-1" />
      {user && (
        <div className="flex items-center gap-3">
          <Badge variant="secondary">
            {user.xp} {tCommon('xp')}
          </Badge>
          {user.is_pro && (
            <Badge variant="default">{tCommon('pro', { fallback: 'Pro' })}</Badge>
          )}
        </div>
      )}
    </header>
  );
}
