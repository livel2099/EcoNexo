import type { MetadataRoute } from "next";

// Required for Next.js static exports (`output: "export"`).
// Without this explicit declaration Next.js 15 can treat the metadata route
// as dynamic and stop the Cloudflare build while collecting page data.
export const dynamic = "force-static";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: "*",
        allow: [
          "/",
          "/reportar",
          "/terminos",
          "/privacidad",
          "/cookies",
          "/seguridad",
          "/accesibilidad",
        ],
        disallow: ["/dashboard", "/informe"],
      },
    ],
  };
}
