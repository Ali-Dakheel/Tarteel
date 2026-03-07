'use client';

import DOMPurify from 'dompurify';

type Props = { content: string };

export function LessonContent({ content }: Props) {
  const clean = DOMPurify.sanitize(content);

  return (
    <div
      className="prose prose-neutral max-w-none dark:prose-invert
        prose-headings:font-semibold prose-p:leading-relaxed
        prose-code:rounded prose-code:bg-muted prose-code:px-1 prose-code:py-0.5
        prose-pre:bg-muted [&_pre]:font-mono [&_code]:text-sm"
    >
      {/* Technical terms inside Arabic text should be LTR */}
      <div
        className="whitespace-pre-wrap"
        dangerouslySetInnerHTML={{ __html: clean }}
      />
    </div>
  );
}
