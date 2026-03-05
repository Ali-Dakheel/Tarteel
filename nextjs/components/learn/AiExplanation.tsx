'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { explainSSE } from '@/lib/api/tutor';
import type { ExplainPayload } from '@/lib/api/tutor';
import { cn } from '@/lib/utils';
import { Sparkles, AlertCircle, Bot } from 'lucide-react';

type Props = {
  payload: ExplainPayload;
  autoStart?: boolean;
  variant?: 'card' | 'chat';
  onScrollNeeded?: () => void;
  onDone?: () => void;
};

export function AiExplanation({ payload, autoStart = false, variant = 'card', onScrollNeeded, onDone }: Props) {
  const t = useTranslations('lesson');
  const tTutor = useTranslations('tutor');

  const [text, setText] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!autoStart) return;

    let aborted = false;

    setLoading(true);
    setText('');
    setError('');

    explainSSE(
      payload,
      (chunk) => {
        if (aborted) return;
        setText((prev) => prev + chunk);
        // In card mode scroll the internal container; in chat mode notify parent
        if (variant === 'card' && containerRef.current) {
          containerRef.current.scrollTop = containerRef.current.scrollHeight;
        } else {
          onScrollNeeded?.();
        }
      },
      () => {
        if (aborted) return;
        setLoading(false);
        onDone?.();
      },
      (err) => {
        if (aborted) return;
        setLoading(false);
        setError(err.message);
        onDone?.();
      },
    );

    return () => { aborted = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoStart, payload.question_id, payload.selected_option, payload.question_stem]);

  if (!loading && !text && !error) return null;

  // ── Chat variant ─────────────────────────────────────────────────────────
  if (variant === 'chat') {
    return (
      <div className="flex gap-3 max-w-[85%]">
        <div className="h-7 w-7 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
          <Bot className="h-4 w-4 text-primary" />
        </div>
        <div className="text-sm leading-relaxed" dir="auto">
          {error ? (
            <span className="flex items-center gap-1.5 text-destructive">
              <AlertCircle className="h-3.5 w-3.5" />
              {tTutor('error')}
            </span>
          ) : (
            <span className="whitespace-pre-wrap">
              {text || (loading && <span className="text-muted-foreground animate-pulse">Thinking…</span>)}
              {loading && text && (
                <span className="inline-block h-4 w-0.5 animate-pulse bg-primary ms-0.5" />
              )}
            </span>
          )}
        </div>
      </div>
    );
  }

  // ── Card variant (lesson page) ────────────────────────────────────────────
  return (
    <div className="rounded-xl border bg-muted/40 p-5 space-y-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-primary">
        <Sparkles className="h-4 w-4" />
        {t('explanation')}
      </div>

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
            '[&_code]:ltr [&_code]:font-mono [&_code]:text-xs',
          )}
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
