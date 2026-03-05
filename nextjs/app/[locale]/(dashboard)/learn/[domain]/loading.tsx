export default function DomainLoading() {
  return (
    <div className="mx-auto max-w-2xl space-y-4">
      <div className="h-8 w-48 animate-pulse rounded bg-muted" />
      <div className="h-6 w-24 animate-pulse rounded bg-muted" />
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="h-20 animate-pulse rounded-xl bg-muted" />
      ))}
    </div>
  );
}
