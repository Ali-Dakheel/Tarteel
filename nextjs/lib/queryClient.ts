import { QueryClient } from '@tanstack/react-query';
import { cache } from 'react';

// cache() ensures one QueryClient per request in Server Components
export const getQueryClient = cache(
  () =>
    new QueryClient({
      defaultOptions: {
        queries: {
          staleTime: 60 * 1000, // 1 minute default — override per query as needed
          retry: 1,
        },
      },
    }),
);
