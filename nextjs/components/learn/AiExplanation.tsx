'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { explainSSE } from '@/lib/api/tutor';
import type { ExplainPayload } from '@/lib/api/tutor';
import { cn } from '@/lib/utils';
import { Sparkles, AlertCircle } from 'lucide-react';

type Props = {
  payload: ExplainPayload;
  autoStart?: boolean;
};

export function AiExplanation({ payload, autoStart = false }: Props) {
  const t = useTranslations('lesson');
  const tTutor = useTranslations('tutor');

  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!autoStart) return;

    // Local flag — each effect invocation owns its own abort state.
    // Using a ref would share state across the two calls React Strict Mode makes,
    // causing the first (cleaned-up) stream to append after the ref is reset.
    let aborted = false;

    setLoading(true);
    setText('');
    setDone(false);
    setError('');

    explainSSE(
      payload,
      (chunk) => {
        if (aborted) return;
        setText((prev) => prev + chunk);
        if (containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
        }
      },
      () => {
        if (aborted) return;
        setLoading(false);
        setDone(true);
      },
      (err) => {
        if (aborted) return;
        setLoading(false);
        setError(err.message);
      },
    );

    return () => { aborted = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStart, payload.question_id, payload.selected_option, payload.question_stem]);

  if (!loading && !text && !error) return null;

  return (
    <div className="rounded-xl border bg-muted/40 p-5 space-y-3">
      {/* Header */}
      <div className="flex items-center gap-2 text-sm font-semibold text-primary">
        <Sparkles className="h-4 w-4" />
        {t('explanation')}
      </div>

      {/* Content */}
      {error ? (
        <div className="flex items-center gap-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4" />
          {tTutor('error')}
        </div>
      ) : (
        <div
          ref={containerRef}
          className={cn(
            'max-h-96 overflow-y-auto text-sm leading-relaxed whitespace-pre-wrap',
            // Arabic text is RTL, technical terms in LTR
            '[&_code]:ltr [&_code]:font-mono [&_code]:text-xs',
          )}
          // The AI produces Arabic text — browser will auto-detect text direction
          dir="auto"
        >
          {text}
          {loading && (
            <span className="inline-block h-4 w-0.5 animate-pulse bg-primary ms-0.5" />
          )}
        </div>
      )}

      {loading && !text && (
        <p className="text-xs text-muted-foreground">{t('loadingExplanation')}</p>
      )}
    </div>
  );
}
