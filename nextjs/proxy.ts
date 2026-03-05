import createMiddleware from 'next-intl/middleware';
import { type NextRequest, NextResponse } from 'next/server';
import { routing } from './i18n/routing';

const handleI18n = createMiddleware(routing);

const LOCALE_PATTERN = /^\/(ar|en)(\/|$)/;
const AUTH_PATHS = /^\/(ar|en)\/(login|register)(\/|$)/;

export function proxy(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const token = request.cookies.get('tarteel_token')?.value;

  const localeMatch = LOCALE_PATTERN.exec(pathname);
  const isLocaleRoute = localeMatch !== null;
  const isAuthPage = AUTH_PATHS.test(pathname);
  const isDashboardPage = isLocaleRoute && !isAuthPage;

  // Redirect unauthenticated users away from dashboard routes
  if (isDashboardPage && !token) {
    const locale = localeMatch![1];
    return NextResponse.redirect(new URL(`/${locale}/login`, request.url));
  }

  // Redirect authenticated users away from login/register
  if (isAuthPage && token) {
    const locale = localeMatch![1];
    return NextResponse.redirect(new URL(`/${locale}`, request.url));
  }

  return handleI18n(request) as NextResponse;
}

export const config = {
  // Match all routes except Next.js internals and static files
  matcher: ['/((?!_next|.*\\..*).*)'],
};
