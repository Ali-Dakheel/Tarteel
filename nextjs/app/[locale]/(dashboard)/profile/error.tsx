'use client';

import { Button } from '@/components/ui/button';

export default function ProfileError({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-20 gap-4 text-center">
      <p className="text-lg font-semibold">Failed to load profile</p>
      <Button variant="outline" onClick={reset}>
        Try again
      </Button>
    </div>
  );
}
