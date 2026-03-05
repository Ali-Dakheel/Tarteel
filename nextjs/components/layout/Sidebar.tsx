'use client';

import { useTranslations } from 'next-intl';
import { usePathname } from 'next/navigation';
import { Link } from '@/i18n/navigation';
import { cn } from '@/lib/utils';
import { Home, MessageSquare, User } from 'lucide-react';

const NAV_ITEMS = [
  { href: '/', icon: Home, labelKey: 'home' },
  { href: '/tutor', icon: MessageSquare, labelKey: 'tutor' },
  { href: '/profile', icon: User, labelKey: 'profile' },
] as const;

export function Sidebar() {
  const t = useTranslations('nav');
  const pathname = usePathname();

  return (
    <aside className="hidden w-56 shrink-0 border-e bg-card md:flex md:flex-col">
      {/* Logo */}
      <div className="flex h-16 items-center px-6 border-b">
        <span className="text-xl font-bold text-primary">تَرتيل</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 space-y-1 p-3">
        {NAV_ITEMS.map(({ href, icon: Icon, labelKey }) => {
          const isActive = pathname.includes(href === '/' ? '/ar' : href) && href !== '/';
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground',
              )}
            >
              <Icon className="h-4 w-4" />
              {t(labelKey)}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
