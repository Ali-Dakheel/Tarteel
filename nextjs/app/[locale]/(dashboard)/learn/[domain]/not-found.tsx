import { Link } from '@/i18n/navigation';

export default function DomainNotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
      <h1 className="text-4xl font-bold">404</h1>
      <p className="text-muted-foreground">Domain not found</p>
      <Link href="/" className="text-primary underline">
        Back to domains
      </Link>
    </div>
  );
}
