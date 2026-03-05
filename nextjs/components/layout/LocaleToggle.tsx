'use client';

import { useRouter, usePathname } from '@/i18n/navigation';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';

type Props = { currentLocale: string };

export function LocaleToggle({ currentLocale }: Props) {
  const t = useTranslations('profile');
  const router = useRouter();
  const pathname = usePathname();

  const switchTo = currentLocale === 'ar' ? 'en' : 'ar';

  const handleSwitch = () => {
    router.replace(pathname, { locale: switchTo });
  };

  return (
    <div className="flex items-center gap-3">
      <span className="text-sm text-muted-foreground">
        {currentLocale === 'ar' ? t('arabic') : t('english')}
      </span>
      <Button variant="outline" size="sm" onClick={handleSwitch}>
        {switchTo === 'ar' ? t('arabic') : t('english')}
      </Button>
    </div>
  );
}
