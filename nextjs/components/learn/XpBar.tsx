import { useTranslations } from 'next-intl';
import { Progress } from '@/components/ui/progress';
import { Star } from 'lucide-react';

type Props = { xp: number };

const XP_PER_LEVEL = 100;

export function XpBar({ xp }: Props) {
  const t = useTranslations('profile');
  const level = Math.floor(xp / XP_PER_LEVEL) + 1;
  const progress = xp % XP_PER_LEVEL;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-1.5">
          <Star className="h-4 w-4 text-yellow-500" />
          <span className="font-semibold">
            {xp} {t('xp')}
          </span>
        </div>
        <span className="text-xs text-muted-foreground">Level {level}</span>
      </div>
      <Progress value={progress} className="h-2" />
      <p className="text-xs text-muted-foreground">
        {progress}/{XP_PER_LEVEL} to level {level + 1}
      </p>
    </div>
  );
}
