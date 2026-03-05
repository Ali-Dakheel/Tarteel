@AGENTS.md

---

# Tarteel Next.js — Project Rules

## Architecture

- **BFF pattern**: All API calls go through Next.js `/app/api/*` route handlers → `lib/server/laravel.ts` reads httpOnly `tarteel_token` cookie → forwards to Laravel. Client JS never touches the token.
- **SSE**: `app/api/tutor/explain/route.ts` proxies the stream. Client uses `fetch + ReadableStream`, never EventSource.
- **Auth guard**: `proxy.ts` (Next.js 16) reads the `tarteel_token` cookie. Dashboard routes redirect to `/[locale]/login` if missing.
- **i18n**: `next-intl` with `[locale]` segment. Locales: `ar` (default), `en`.

---

# Next.js App Router + TanStack Query Rules

## 1. Next.js App Router — Non-Negotiables

### Server vs Client Components
- **Default is Server Component.** Only add `"use client"` when you actually need browser APIs, hooks, or event handlers.
- A Server Component can import and render Client Components. The reverse is not true — never import a Server Component into a Client Component.
- **`generateMetadata()` can only be exported from Server Components.** If a page needs both metadata and interactivity, split it: a Server Component wrapper (page.tsx) exports `generateMetadata()` and renders a `"use client"` child component.
- **`useSearchParams()` in a Client Component requires a `<Suspense>` boundary** higher in the tree during SSR, or the build will warn/fail.

### File Conventions
Every route segment should have:
- `page.tsx` — the page itself
- `loading.tsx` — Suspense skeleton (shown instantly during navigation)
- `error.tsx` — `"use client"` error boundary (`"use client"`, receives `error` + `reset` props)
- `not-found.tsx` — rendered when `notFound()` is called in that segment

Missing any of these is a UX dead end. Create stubs at minimum.

### Data Access Layer (DAL)
- `lib/server/laravel.ts` has `import 'server-only'` — build error if accidentally imported in a Client Component.

### `params` in App Router
- In Next.js 16, `params` is a Promise: `const { id } = await params` in Server Components.
- In Client Components use `useParams<{ id: string }>()` — no async needed.

### `cookies()` and `headers()` in Next.js 16
- Fully async — always `await cookies()` and `await headers()`.

### API URL prefix bug — classic gotcha
If `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` and you also append `/api/v1/...` to paths, you get `/api/v1/api/v1/...`. In this project, client calls go to `/api/*` (same-origin Next.js routes), not directly to Laravel.

---

## 2. TanStack Query — Rules

### Defaults to know
| Setting | Default | What it means |
|---|---|---|
| `staleTime` | `0` | Data is stale immediately — always refetches on mount unless you set this |
| `gcTime` | `5 min` | Unused cache cleared after 5 minutes |
| `retry` | `3` | Failed queries retry 3 times with exponential backoff |
| `refetchOnWindowFocus` | `true` | Queries refetch when the window regains focus |

**Always set `staleTime`** — minimum `60 * 1000` for content, `5 * 60 * 1000` for user/auth data.

### Query Key Factory — always use this pattern
```ts
// lib/queryKeys.ts — as const, no satisfies (avoids TS7022 circular self-reference)
export const queryKeys = {
  user: { me: () => ['user', 'me'] as const },
  // ...
} as const;
```

### `queryOptions()` helper — use it
```ts
export const domainQueries = {
  all: () => queryOptions({ queryKey: queryKeys.domains.all(), queryFn: getDomains, staleTime: 60_000 }),
};
```

### `isPending` not `isLoading` inside HydrationBoundary
`isPending` is true when there is no data yet — even with prefetch. `isLoading` is false when data is prefetched.

### Optimistic Updates — three-step pattern
```ts
useMutation({
  mutationFn: updateItem,
  onMutate: async (newData) => {
    await queryClient.cancelQueries({ queryKey: ... });
    const previous = queryClient.getQueryData(...);
    queryClient.setQueryData(..., (old) => [...old, newData]);
    return { previous };
  },
  onError: (_err, _data, context) => queryClient.setQueryData(..., context?.previous),
  onSettled: () => queryClient.invalidateQueries({ queryKey: ... }),
});
```

---

## 3. API Response Handling

### Always expect the wrapper — never assume flat
Laravel returns `{ data: {...} }` or `{ data: [...] }`.
```ts
// ✅ Always unwrap:
const domains = (response as { data: Domain[] }).data;
```

### Normalize in the API function — don't leak backend shape to components

---

## 4. TypeScript Gotchas

### String index signatures
```ts
(LABELS as Record<string, string>)[status] ?? status  // not LABELS[status]
```

### zodResolver type mismatch with `.default()`
```ts
resolver: zodResolver(schema) as Resolver<FormOutputType>
```

### `satisfies` + self-referential objects = TS7022
Don't use `satisfies Record<string, KeyFactory>` on self-referencing objects. Use `as const`.

### Number coercion from API
```ts
const price = Number(item.price_snapshot); // handles string | number
```

---

## 5. Authentication

- Token is stored in httpOnly `tarteel_token` cookie — **never exposed to JS**.
- Client calls go to `/api/*` Next.js route handlers.
- Route handlers use `laravelFetch()` from `lib/server/laravel.ts`.
- `proxy.ts` (NOT `middleware.ts` — Next.js 16 rename) handles auth guard + i18n routing.
- Logout: POST `/api/auth/logout` → clears cookie server-side.

---

## 6. i18n (next-intl)

### Don't hardcode locale in hrefs
```tsx
// ❌ <Link href="/en/products">
// ✅
import { Link } from "@/i18n/navigation";
<Link href="/products">
```

### Translation key conventions
- Group by feature: `auth.*`, `domains.*`, `lesson.*`, `tutor.*`, `profile.*`, `common.*`
- Keys camelCase: `lesson.submitAnswer`, not `lesson.submit_answer`
- Both `en.json` and `ar.json` must always be updated together

### Arabic/RTL rules
- `<html lang dir>` is set in `app/[locale]/layout.tsx` based on locale
- Technical terms always bilingual: `إدارة المخاطر (Risk Management)`
- `dir="ltr"` on email/password inputs and code blocks even inside Arabic text
- `dir="auto"` on AI-generated text (mixed Arabic/English)
- Use `rtl:` / `ltr:` Tailwind modifiers for directional layout
- `ms-*` / `me-*` (margin-start/end) instead of `ml-*` / `mr-*` for RTL compatibility

---

## 7. UX Dead Ends — Never Ship These

- Every link must go somewhere — no dead hrefs
- `loading.tsx` required in every route segment
- `error.tsx` required in every route segment
- `not-found.tsx` required in every route segment
- Pro-locked lessons show "Pro Required" badge, not a blank error
- Streak 0 is still valid — don't hide the StreakBadge

---

## 8. Performance

### Prefetch on hover
```ts
const handleMouseEnter = () => {
  queryClient.prefetchQuery({ queryKey: queryKeys.domains.all(), queryFn: getDomains, staleTime: 60_000 });
};
```

---

## 9. Security Checklist

- [ ] `server-only` in `lib/server/laravel.ts` — prevents token leak to client
- [ ] No `NEXT_PUBLIC_*` for sensitive values (LARAVEL_URL is server-only)
- [ ] `httpOnly` cookie for auth token
- [ ] `SameSite=lax` on auth cookie
- [ ] Input validated at API boundaries — zod on forms
- [ ] `dir="ltr"` on email/password inputs (prevents RTL injection)
