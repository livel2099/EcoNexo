import type { MetadataRoute } from "next";

// Required for Next.js static exports (`output: "export"`).
export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  const base = process.env.NEXT_PUBLIC_APP_URL || "https://econexo.example";

  return [
    "",
    "/reportar",
    "/terminos",
    "/privacidad",
    "/cookies",
    "/seguridad",
    "/accesibilidad",
    "/metodologia",
    "/estado",
  ].map((path) => ({
    url: `${base}${path}`,
    lastModified: new Date("2026-07-27T00:00:00Z"),
    changeFrequency: path === "" ? ("weekly" as const) : ("monthly" as const),
    priority: path === "" ? 1 : path === "/reportar" ? 0.8 : 0.4,
  }));
}
