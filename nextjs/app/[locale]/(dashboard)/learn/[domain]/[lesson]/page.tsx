'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import { useState, useRef } from 'react';
import { useParams } from 'next/navigation';
import { getLesson, markProgress } from '@/lib/api/lessons';
import { submitAttempt } from '@/lib/api/questions';
import { queryKeys } from '@/lib/queryKeys';
import { LessonContent } from '@/components/learn/LessonContent';
import { QuestionCard } from '@/components/learn/QuestionCard';
import { Link } from '@/i18n/navigation';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { Lesson, QuestionAttempt } from '@/types/api';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export default function LessonPage() {
  const t = useTranslations('lesson');
  const tCommon = useTranslations('common');
  const params = useParams<{ locale: string; domain: string; lesson: string }>();
  const queryClient = useQueryClient();

  const [currentQ, setCurrentQ] = useState(0);
  const [attempts, setAttempts] = useState<Record<number, QuestionAttempt>>({});
  const startTime = useRef(Date.now());

  const {
    data: lesson,
    isPending,
    error,
  } = useQuery<Lesson>({
    queryKey: queryKeys.lessons.detail(params.lesson),
    queryFn: () => getLesson(params.lesson),
    staleTime: 5 * 60 * 1000,
  });

  const completeMutation = useMutation({
    mutationFn: () =>
      markProgress(params.lesson, Math.floor((Date.now() - startTime.current) / 1000)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.progress.all() });
      queryClient.invalidateQueries({ queryKey: queryKeys.lessons.detail(params.lesson) });
    },
  });

  const handleAttempt = (questionId: number, attempt: QuestionAttempt) => {
    setAttempts((prev) => ({ ...prev, [questionId]: attempt }));
  };

  if (isPending) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded bg-muted" />
        <div className="h-64 animate-pulse rounded-xl bg-muted" />
      </div>
    );
  }

  if (error) {
    const isProRequired = error.message === 'pro_required';
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
        <p className="text-lg font-semibold">
          {isProRequired ? tCommon('pro') : tCommon('error')}
        </p>
        <Link href={`/learn/${params.domain}`}>
          <Button variant="outline">{t('backToDomain')}</Button>
        </Link>
      </div>
    );
  }

  const questions = lesson.questions ?? [];
  const question = questions[currentQ];
  const isCompleted = !!lesson.user_progress?.completed_at;

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link href={`/learn/${params.domain}`}>
          <Button variant="ghost" size="sm">
            <ChevronLeft className="h-4 w-4 rtl:rotate-180" />
            {t('backToDomain')}
          </Button>
        </Link>
      </div>

      <div>
        <h1 className="text-2xl font-bold">{lesson.title}</h1>
        <div className="mt-2 flex items-center gap-2">
          <Badge variant="outline">
            {params.domain.replace('-', ' ')}
          </Badge>
          {lesson.is_free && <Badge variant="secondary">{tCommon('free')}</Badge>}
        </div>
      </div>

      {/* Lesson Content */}
      <LessonContent content={lesson.content} />

      {/* Questions */}
      {questions.length > 0 && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">
            {t('questions')} — {t('question')} {currentQ + 1} {t('of')} {questions.length}
          </h2>

          <QuestionCard
            key={question.id}
            question={question}
            attempt={attempts[question.id]}
            lessonId={lesson.id}
            domain={params.domain}
            onAttempt={handleAttempt}
          />

          {/* Navigation */}
          <div className="flex justify-between">
            <Button
              variant="outline"
              onClick={() => setCurrentQ((q) => q - 1)}
              disabled={currentQ === 0}
            >
              <ChevronLeft className="h-4 w-4 rtl:rotate-180" />
              {t('back', { ns: 'common' })}
            </Button>
            {currentQ < questions.length - 1 ? (
              <Button onClick={() => setCurrentQ((q) => q + 1)}>
                {t('nextLesson')}
                <ChevronRight className="h-4 w-4 rtl:rotate-180" />
              </Button>
            ) : (
              <Button
                onClick={() => completeMutation.mutate()}
                disabled={isCompleted || completeMutation.isPending}
              >
                {isCompleted ? '✓' : t('markComplete')}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
