export default function LessonLoading() {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <div className="h-8 w-32 animate-pulse rounded bg-muted" />
      <div className="h-10 w-64 animate-pulse rounded bg-muted" />
      <div className="space-y-3">
        {[1, 2, 3, 4, 5].map((i) => (
          <div key={i} className="h-4 animate-pulse rounded bg-muted" style={{ width: `${70 + i * 5}%` }} />
        ))}
      </div>
      <div className="h-48 animate-pulse rounded-xl bg-muted" />
    </div>
  );
}
