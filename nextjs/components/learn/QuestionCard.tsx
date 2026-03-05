'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { submitAttempt } from '@/lib/api/questions';
import { AiExplanation } from './AiExplanation';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { queryKeys } from '@/lib/queryKeys';
import type { Question, QuestionAttempt } from '@/types/api';
import type { ExplainPayload } from '@/lib/api/tutor';
import { CheckCircle, XCircle } from 'lucide-react';

type Props = {
  question: Question;
  attempt: QuestionAttempt | undefined;
  lessonId: number;
  domain: string;
  onAttempt: (questionId: number, attempt: QuestionAttempt) => void;
};

const OPTION_LABELS = ['A', 'B', 'C', 'D'];

export function QuestionCard({ question, attempt, lessonId, domain, onAttempt }: Props) {
  const t = useTranslations('lesson');
  const queryClient = useQueryClient();
  const [selected, setSelected] = useState<number | null>(null);

  const mutation = useMutation({
    mutationFn: (option: number) => submitAttempt(question.id, option),
    onSuccess: (result) => {
      onAttempt(question.id, result);
      // Invalidate streak + progress after XP award
      queryClient.invalidateQueries({ queryKey: queryKeys.streak.all() });
      queryClient.invalidateQueries({ queryKey: queryKeys.user.me() });
    },
  });

  const handleSubmit = () => {
    if (selected === null) return;
    mutation.mutate(selected);
  };

  const answered = !!attempt;
  const difficultyColor = {
    easy: 'bg-green-100 text-green-700',
    medium: 'bg-yellow-100 text-yellow-700',
    hard: 'bg-red-100 text-red-700',
  } as const;

  const explainPayload: ExplainPayload = {
    question_id: question.id,
    selected_option: attempt?.selected_option ?? 0,
    lesson_id: lessonId,
    domain,
    question_stem: question.stem,
  };

  return (
    <div className="rounded-xl border bg-card p-6 space-y-5">
      {/* Question stem */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <Badge
            className={cn('text-xs', difficultyColor[question.difficulty])}
            variant="outline"
          >
            {t(`difficulty.${question.difficulty}`)}
          </Badge>
        </div>
        <p className="text-base font-medium leading-relaxed">{question.stem}</p>
      </div>

      {/* Options */}
      <div className="space-y-2">
        {question.options.map((option, idx) => {
          const isSelected = selected === idx;
          const isCorrect = answered && attempt.correct_option === idx;
          const isWrong = answered && attempt.selected_option === idx && !attempt.is_correct;

          return (
            <button
              key={idx}
              onClick={() => !answered && setSelected(idx)}
              disabled={answered}
              className={cn(
                'flex w-full items-start gap-3 rounded-lg border px-4 py-3 text-start text-sm transition-colors',
                !answered && isSelected && 'border-primary bg-primary/5',
                !answered && !isSelected && 'hover:bg-accent',
                answered && isCorrect && 'border-green-500 bg-green-50 text-green-800 dark:bg-green-950',
                answered && isWrong && 'border-red-400 bg-red-50 text-red-800 dark:bg-red-950',
                answered && !isCorrect && !isWrong && 'opacity-50',
              )}
            >
              <span className="shrink-0 font-mono text-xs font-semibold">
                {OPTION_LABELS[idx]}
              </span>
              <span className="flex-1">{option}</span>
              {answered && isCorrect && (
                <CheckCircle className="h-4 w-4 shrink-0 text-green-600" />
              )}
              {answered && isWrong && (
                <XCircle className="h-4 w-4 shrink-0 text-red-500" />
              )}
            </button>
          );
        })}
      </div>

      {/* Submit */}
      {!answered && (
        <Button
          onClick={handleSubmit}
          disabled={selected === null || mutation.isPending}
          className="w-full"
        >
          {mutation.isPending ? '...' : t('submitAnswer')}
        </Button>
      )}

      {/* Result feedback */}
      {answered && (
        <div
          className={cn(
            'flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium',
            attempt.is_correct
              ? 'bg-green-50 text-green-700 dark:bg-green-950'
              : 'bg-red-50 text-red-700 dark:bg-red-950',
          )}
        >
          {attempt.is_correct ? (
            <>
              <CheckCircle className="h-4 w-4" />
              {t('correct')}
            </>
          ) : (
            <>
              <XCircle className="h-4 w-4" />
              {t('incorrect')}
            </>
          )}
        </div>
      )}

      {/* AI Explanation — auto-streams on wrong answer */}
      {answered && !attempt.is_correct && (
        <AiExplanation payload={explainPayload} autoStart />
      )}
    </div>
  );
}
