import { parseApiError } from '@/lib/api/errors';
import type { QuestionAttempt } from '@/types/api';

export async function submitAttempt(
  questionId: number,
  selectedOption: number,
): Promise<QuestionAttempt> {
  const res = await fetch(`/api/questions/${questionId}/attempt`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ selected_option: selectedOption }),
  });
  if (!res.ok) {
    throw new Error(await parseApiError(res, 'Failed to submit answer'));
  }
  const body = await res.json() as { data: QuestionAttempt };
  return body.data;
}
