import type { Metadata } from "next";

import { WikiWidget } from "@/features/wiki/WikiWidget";
import "maplibre-gl/dist/maplibre-gl.css";
import "./globals.css";

export const metadata: Metadata = {
  title: "GAIA | Gestione Apparati Informativi",
  description: "Piattaforma IT governance del Consorzio di Bonifica dell'Oristanese",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="it">
      <body>
        {children}
        <WikiWidget />
      </body>
    </html>
  );
}
