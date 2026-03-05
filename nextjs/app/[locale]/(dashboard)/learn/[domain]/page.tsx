'use client';

import { useQuery } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { useParams } from 'next/navigation';
import { getDomainLessons } from '@/lib/api/domains';
import { queryKeys } from '@/lib/queryKeys';
import { Link } from '@/i18n/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronLeft, ChevronRight, CheckCircle, Lock, BookOpen } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { Lesson } from '@/types/api';

export default function DomainPage() {
  const t = useTranslations('lesson');
  const tDomains = useTranslations('domains');
  const tCommon = useTranslations('common');
  const params = useParams<{ locale: string; domain: string }>();

  const { data: lessons, isPending, error } = useQuery<Lesson[]>({
    queryKey: queryKeys.domains.lessons(params.domain),
    queryFn: () => getDomainLessons(params.domain),
    staleTime: 5 * 60 * 1000,
  });

  const domainName = params.domain
    .split('-')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');

  if (isPending) {
    return (
      <div className="mx-auto max-w-2xl space-y-4">
        <div className="h-8 w-48 animate-pulse rounded bg-muted" />
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-20 animate-pulse rounded-xl bg-muted" />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
        <p className="text-lg font-semibold">{tCommon('error')}</p>
        <Link href="/">
          <Button variant="outline">{tCommon('back')}</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href="/">
          <Button variant="ghost" size="sm">
            <ChevronLeft className="h-4 w-4 rtl:rotate-180" />
            {tDomains('title')}
          </Button>
        </Link>
      </div>

      <div>
        <h1 className="text-2xl font-bold">{domainName}</h1>
        <p className="text-muted-foreground mt-1">
          {lessons?.length ?? 0} {tDomains('lessons')}
        </p>
      </div>

      {/* Lessons list */}
      <div className="space-y-3">
        {lessons?.map((lesson, idx) => {
          const isCompleted = !!lesson.user_progress?.completed_at;
          const isLocked = !lesson.is_free;

          return (
            <Link
              key={lesson.id}
              href={isLocked ? '#' : `/learn/${params.domain}/${lesson.slug}`}
              aria-disabled={isLocked}
              tabIndex={isLocked ? -1 : undefined}
            >
              <Card
                className={cn(
                  'transition-shadow',
                  !isLocked && 'cursor-pointer hover:shadow-md',
                  isLocked && 'opacity-60 cursor-not-allowed',
                )}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      <span className="shrink-0 flex h-7 w-7 items-center justify-center rounded-full bg-muted text-xs font-semibold">
                        {isCompleted ? (
                          <CheckCircle className="h-4 w-4 text-green-600" />
                        ) : (
                          idx + 1
                        )}
                      </span>
                      <CardTitle className="text-base leading-snug">{lesson.title}</CardTitle>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {lesson.is_free ? (
                        <Badge variant="secondary" className="text-xs">
                          {tCommon('free')}
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="text-xs gap-1">
                          <Lock className="h-3 w-3" />
                          {tCommon('pro')}
                        </Badge>
                      )}
                      {isCompleted && (
                        <Badge className="text-xs bg-green-100 text-green-700 border-green-200">
                          ✓
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardHeader>
                {lesson.question_count !== undefined && lesson.question_count > 0 && (
                  <CardContent className="pt-0">
                    <div className="flex items-center gap-1.5 text-xs text-muted-foreground ms-10">
                      <BookOpen className="h-3.5 w-3.5" />
                      {lesson.question_count} {t('questions')}
                      <ChevronRight className="h-3.5 w-3.5 ms-auto rtl:rotate-180" />
                    </div>
                  </CardContent>
                )}
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
