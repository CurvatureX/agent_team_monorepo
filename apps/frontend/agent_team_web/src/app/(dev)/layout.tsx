import { notFound } from 'next/navigation';

export default function DevLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  // Only allow access in development mode
  if (process.env.NODE_ENV === 'production') {
    notFound();
  }

  return <>{children}</>;
}