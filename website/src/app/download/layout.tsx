import { pageMetadata } from '@/lib/metadata';

export const metadata = pageMetadata(
  '/download/',
  "Download SentryPhi for Windows and Linux",
  "Get the Windows installer, check Linux availability, and review system requirements before your first model security scan.",
);

export default function DownloadLayout({ children }: { children: React.ReactNode }) {
  return children;
}
