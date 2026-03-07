'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { AiExplanation } from '@/components/learn/AiExplanation';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send, BookOpen } from 'lucide-react';

type Message = {
  id: string;
  question: string; // frozen snapshot at submit time — never mutated
};

const STARTERS = [
  'What do projects enable organizations to do?',
  'What is the difference between a project and operations?',
  'What is the role of the project sponsor?',
];

export default function TutorPage() {
  const t = useTranslations('tutor');

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () =>
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });

  const submit = (question: string) => {
    const trimmed = question.trim();
    if (!trimmed || isStreaming) return;
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), question: trimmed }]);
    setInput('');
    setIsStreaming(true);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      setTimeout(() => textareaRef.current?.focus(), 0);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submit(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit(input);
    }
  };

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 200)}px`;
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">

      {/* ── Messages ─────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-4">
            <div className="h-14 w-14 rounded-2xl bg-primary/10 flex items-center justify-center">
              <BookOpen className="h-7 w-7 text-primary" />
            </div>
            <div>
              <p className="text-lg font-semibold">{t('title')}</p>
              <p className="text-sm text-muted-foreground mt-1 max-w-sm">{t('subtitle')}</p>
            </div>
            <div className="flex flex-wrap gap-2 justify-center mt-2">
              {STARTERS.map((s) => (
                <button
                  key={s}
                  onClick={() => submit(s)}
                  className="text-xs px-3 py-1.5 rounded-full border border-border hover:bg-muted transition-colors cursor-pointer"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto px-4 py-6 space-y-8">
            {messages.map((msg, idx) => (
              <div key={msg.id} className="space-y-4">
                {/* User bubble — right aligned */}
                <div className="flex justify-end">
                  <div className="bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[80%] text-sm leading-relaxed">
                    {msg.question}
                  </div>
                </div>

                {/* AI response — msg.question is frozen, never re-triggers on input change */}
                <AiExplanation
                  payload={{
                    question_id: null,
                    selected_option: null,
                    lesson_id: null,
                    domain: null,
                    question_stem: msg.question,
                  }}
                  autoStart
                  variant="chat"
                  onScrollNeeded={scrollToBottom}
                  onDone={idx === messages.length - 1 ? () => setIsStreaming(false) : undefined}
                />
              </div>
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* ── Input bar ────────────────────────────────────── */}
      <div className="border-t bg-background/95 backdrop-blur px-4 py-4">
        <form onSubmit={handleSubmit} className="max-w-3xl mx-auto flex gap-2 items-end">
          <Textarea
            ref={textareaRef}
            value={input}
            onChange={handleInput}
            onKeyDown={handleKeyDown}
            placeholder={t('placeholder')}
            rows={1}
            className="resize-none flex-1 min-h-[44px] max-h-[200px] overflow-y-auto py-3"
            disabled={isStreaming}
          />
          <Button
            type="submit"
            size="icon"
            className="h-[44px] w-[44px] flex-shrink-0"
            disabled={!input.trim() || isStreaming}
          >
            <Send className="h-4 w-4" />
          </Button>
        </form>
        <p className="text-xs text-muted-foreground text-center mt-2">
          Enter ↵ to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  );
}
