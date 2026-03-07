export type ExplainPayload = {
  question_id: number | null;
  selected_option: number | null;
  lesson_id: number | null;
  domain: string | null;
  question_stem: string;
};

/**
 * Stream an AI explanation via SSE.
 * Calls the Next.js proxy route which reads the httpOnly cookie and forwards to Laravel.
 *
 * @param payload   - Question context
 * @param onChunk   - Called with each decoded text chunk as it arrives
 * @param onDone    - Called when the stream ends
 * @param onError   - Called on network or upstream error
 */
export async function explainSSE(
  payload: ExplainPayload,
  onChunk: (text: string) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): Promise<void> {
  try {
    const res = await fetch('/api/tutor/explain', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok || !res.body) {
      onError(new Error('AI service unavailable'));
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by double newlines
      const events = buffer.split('\n\n');
      buffer = events.pop() ?? ''; // keep incomplete last chunk

      for (const event of events) {
        for (const line of event.split('\n')) {
          if (line.startsWith('data: ')) {
            const raw = line.slice(6);
            if (raw === '[DONE]') break;
            try {
              onChunk(JSON.parse(raw) as string);
            } catch {
              if (raw) onChunk(raw);
            }
          }
        }
      }
    }

    onDone();
  } catch (err) {
    onError(err instanceof Error ? err : new Error('Stream error'));
  }
}
