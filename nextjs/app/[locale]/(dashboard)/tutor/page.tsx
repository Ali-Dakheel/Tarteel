'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { AiExplanation } from '@/components/learn/AiExplanation';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const DOMAINS = ['people', 'process', 'business-environment'] as const;

export default function TutorPage() {
  const t = useTranslations('tutor');

  const [stem, setStem] = useState('');
  const [domain, setDomain] = useState<string>('process');
  const [submitted, setSubmitted] = useState(false);
  const [key, setKey] = useState(0); // remount AiExplanation on new question

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!stem.trim()) return;
    setKey((k) => k + 1);
    setSubmitted(true);
  };

  const handleReset = () => {
    setStem('');
    setSubmitted(false);
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold">{t('title')}</h1>
        <p className="mt-1 text-muted-foreground">{t('subtitle')}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label>{t('domainLabel')}</Label>
          <Select value={domain} onValueChange={setDomain}>
            <SelectTrigger className="w-full">
              <SelectValue placeholder={t('domainPlaceholder')} />
            </SelectTrigger>
            <SelectContent>
              {DOMAINS.map((d) => (
                <SelectItem key={d} value={d}>
                  {t(`domains.${d}`)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="question">{t('placeholder')}</Label>
          <Textarea
            id="question"
            value={stem}
            onChange={(e) => setStem(e.target.value)}
            placeholder={t('placeholder')}
            rows={4}
            className="resize-none"
          />
        </div>

        <div className="flex gap-2">
          <Button type="submit" disabled={!stem.trim()}>
            {t('submit')}
          </Button>
          {submitted && (
            <Button type="button" variant="outline" onClick={handleReset}>
              {t('domainPlaceholder')}
            </Button>
          )}
        </div>
      </form>

      {submitted && (
        <AiExplanation
          key={key}
          payload={{
            question_id: null,
            selected_option: null,
            lesson_id: null,
            domain,
            question_stem: stem,
          }}
          autoStart
        />
      )}
    </div>
  );
}
