// Centralized query key factory — as const, no satisfies (avoids TS7022 self-reference)
export const queryKeys = {
  user: {
    me: () => ['user', 'me'] as const,
  },
  domains: {
    all: () => ['domains'] as const,
    lessons: (slug: string) => ['domains', slug, 'lessons'] as const,
  },
  lessons: {
    detail: (slug: string) => ['lessons', slug] as const,
  },
  progress: {
    all: () => ['progress'] as const,
  },
  streak: {
    all: () => ['streak'] as const,
  },
} as const;
