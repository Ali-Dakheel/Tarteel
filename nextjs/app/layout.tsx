// Minimal root layout — next-intl proxy.ts handles locale detection and routing.
// All meaningful layout (html, body, providers) is in app/[locale]/layout.tsx.
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return children;
}
