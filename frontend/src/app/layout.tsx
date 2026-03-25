import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "GAIA | Gestione Apparati Informativi e Accessi",
  description: "Piattaforma IT governance del Consorzio di Bonifica dell'Oristanese",
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
