import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "NAS Access Audit Platform",
  description: "Piattaforma interna per audit e review accessi NAS",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="it">
      <body>{children}</body>
    </html>
  );
}
