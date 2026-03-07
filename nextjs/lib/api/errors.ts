/**
 * Parse a failed API response into a human-readable error message.
 * Tries JSON first, falls back to plain text, then a generic message.
 */
export async function parseApiError(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json() as { message?: string };
    return body.message ?? fallback;
  } catch {
    try {
      const text = await res.text();
      return text || fallback;
    } catch {
      return fallback;
    }
  }
}
