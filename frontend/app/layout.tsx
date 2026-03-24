import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Circle of Lies',
  description: 'Deterministic social strategy simulator with explainable agent heuristics.',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
