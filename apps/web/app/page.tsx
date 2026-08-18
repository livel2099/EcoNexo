"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getSession } from "./lib/api";

export default function Home() {
  const router = useRouter();
  useEffect(() => {
    const session = getSession();
    router.replace(session ? (session.account_type === "community" ? "/red-investigacion" : "/dashboard") : "/login");
  }, [router]);
  return <div className="center muted">Cargando EcoNexo…</div>;
}
