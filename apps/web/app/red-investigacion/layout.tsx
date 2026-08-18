import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "EcoNexoFoI — Comunidad de investigadores",
  description:
    "Una comunidad abierta para publicar investigaciones, proponer áreas de estudio y conectar conocimiento.",
};

export default function ResearchNetworkLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return children;
}
