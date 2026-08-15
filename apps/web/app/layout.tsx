import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "EcoNexo — Centro de Comando",
  description: "Inteligencia bioclimatica activa. Sistema de decision en tiempo real.",
  manifest: "/manifest.webmanifest",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-AR">
      <head>
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
      </head>
      <body>{children}</body>
    </html>
  );
}
