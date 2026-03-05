import { useTranslations } from 'next-intl';
import { Flame } from 'lucide-react';
import type { Streak } from '@/types/api';

type Props = { streak: Streak };

export function StreakBadge({ streak }: Props) {
  const t = useTranslations('profile');

  return (
    <div className="flex items-center gap-4">
      <div className="flex items-center gap-1.5">
        <Flame className="h-5 w-5 text-orange-500" />
        <span className="text-sm font-semibold">
          {streak.current_streak} {t('days')}
        </span>
        <span className="text-xs text-muted-foreground">{t('streak')}</span>
      </div>
      {streak.longest_streak > streak.current_streak && (
        <div className="text-xs text-muted-foreground">
          {t('longestStreak')}: {streak.longest_streak}
        </div>
      )}
    </div>
  );
}
