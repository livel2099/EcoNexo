import type { Metadata, Viewport } from "next";
import "leaflet/dist/leaflet.css";
import "./globals.css";
import CookieConsent from "../components/CookieConsent";
import EcoBotAssistant from "../components/EcoBotAssistant";

export const metadata: Metadata = {
  title: { default: "EcoNexo — Inteligencia bioclimática activa", template: "%s · EcoNexo" },
  description: "Plataforma de decisión ambiental en tiempo real: IoT, observación satelital, reportes ciudadanos e informes institucionales.",
  applicationName: "EcoNexo",
  manifest: "/manifest.webmanifest",
  icons: { icon: "/icon.svg" },
  category: "technology",
};

export const viewport: Viewport = {
  themeColor: "#061115",
  colorScheme: "dark",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-AR">
      <head>
        <link rel="preconnect" href="https://accounts.google.com" />
        <link rel="preconnect" href="https://api.open-meteo.com" />
        <link rel="preconnect" href="https://air-quality-api.open-meteo.com" />
        <link rel="preconnect" href="https://sh.dataspace.copernicus.eu" />
        <link rel="preconnect" href="https://basemaps.cartocdn.com" crossOrigin="anonymous" />
      </head>
      <body>
        {children}
        <CookieConsent />
        <EcoBotAssistant />
      </body>
    </html>
  );
}
