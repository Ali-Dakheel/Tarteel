'use client';

import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { useLocale } from 'next-intl';
import { useRouter } from '@/i18n/navigation';
import { getMe, logout } from '@/lib/api/auth';
import { getStreak } from '@/lib/api/progress';
import { queryKeys } from '@/lib/queryKeys';
import { LocaleToggle } from '@/components/layout/LocaleToggle';
import { XpBar } from '@/components/learn/XpBar';
import { StreakBadge } from '@/components/learn/StreakBadge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { User, Streak } from '@/types/api';

export default function ProfilePage() {
  const t = useTranslations('profile');
  const locale = useLocale();
  const router = useRouter();

  const { data: user, isPending: userPending } = useQuery<User>({
    queryKey: queryKeys.user.me(),
    queryFn: getMe,
    staleTime: 5 * 60 * 1000,
  });

  const { data: streak } = useQuery<Streak>({
    queryKey: queryKeys.streak.all(),
    queryFn: getStreak,
    staleTime: 5 * 60 * 1000,
  });

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  if (userPending) {
    return (
      <div className="mx-auto max-w-lg space-y-4">
        <div className="h-8 w-32 animate-pulse rounded bg-muted" />
        <div className="h-48 animate-pulse rounded-xl bg-muted" />
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <h1 className="text-2xl font-bold">{t('title')}</h1>

      {/* User info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{user?.name}</CardTitle>
          <p className="text-sm text-muted-foreground" dir="ltr">{user?.email}</p>
        </CardHeader>
        <CardContent className="space-y-4">
          {user && <XpBar xp={user.xp} />}
          {streak && <StreakBadge streak={streak} />}
        </CardContent>
      </Card>

      {/* Subscription */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t('subscription')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-center gap-2">
            <Badge variant={user?.is_pro ? 'default' : 'secondary'}>
              {user?.is_pro ? t('pro') : t('free')}
            </Badge>
          </div>
          {!user?.is_pro && (
            <Button className="w-full" variant="default">
              {t('upgradeToPro')}
            </Button>
          )}
        </CardContent>
      </Card>

      {/* Language */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t('language')}</CardTitle>
        </CardHeader>
        <CardContent>
          <LocaleToggle currentLocale={locale} />
        </CardContent>
      </Card>

      {/* Logout */}
      <Button variant="outline" className="w-full" onClick={handleLogout}>
        {useTranslations('auth')('logout')}
      </Button>
    </div>
  );
}
