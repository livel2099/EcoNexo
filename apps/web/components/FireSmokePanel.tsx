"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { apiGet, apiPost } from "../app/lib/api";
import type { EarthIntel } from "../app/lib/earth-intel";
import type { Alert, AlertShareInput, AlertShareResult, Detection, Device, EnvironmentalSourceSettings, ModuleEntitlement, Org, RiskZone } from "../app/lib/types";
import { isInMisiones, misionesLocationLabel } from "../app/lib/misiones";

const MapView = dynamic(() => import("./MapView"), { ssr: false });

function distanceKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const r = 6371;
  const toRad = (value: number) => value * Math.PI / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return r * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function fmt(value: number | null | undefined, suffix = "", digits = 0): string {
  return value == null || !Number.isFinite(value) ? "s/d" : `${value.toFixed(digits)}${suffix}`;
}

function relative(iso: string): string {
  const minutes = Math.max(0, Math.round((Date.now() - new Date(iso).getTime()) / 60_000));
  if (minutes < 60) return `hace ${minutes} min`;
  if (minutes < 1440) return `hace ${Math.round(minutes / 60)} h`;
  return `hace ${Math.round(minutes / 1440)} d`;
}

export default function FireSmokePanel({
  token,
  org,
  devices,
  alerts,
  detections,
  zones,
  earth,
  center,
  sourceSettings,
}: {
  token: string;
  org: Org | null;
  devices: Device[];
  alerts: Alert[];
  detections: Detection[];
  zones: RiskZone[];
  earth: EarthIntel | null;
  center: [number, number];
  sourceSettings: EnvironmentalSourceSettings;
}) {
  const [modules, setModules] = useState<ModuleEntitlement[]>([]);
  const [notice, setNotice] = useState("");
  const [sharing, setSharing] = useState(false);

  useEffect(() => {
    void apiGet<ModuleEntitlement[]>("/modules/me", token).then(setModules).catch(() => setModules([]));
  }, [token]);

  const license = modules.find((item) => item.module_key === "fire_smoke");
  const recent = useMemo(() => detections
    .filter((item) => isInMisiones(item.lat, item.lon) && Date.now() - new Date(item.acquired_at).getTime() <= 48 * 3_600_000)
    .map((item) => ({ item, distance: distanceKm(center[0], center[1], item.lat, item.lon) }))
    .sort((a, b) => a.distance - b.distance), [center, detections]);
  const fireAlerts = alerts.filter((item) => isInMisiones(item.lat, item.lon) && item.type === "incendio" && !["descartada", "resuelta"].includes(item.status));
  const nearest = recent[0];
  const dry = (earth?.weather.soilMoisture ?? 0.3) < 0.18 || (earth?.weather.humidity ?? 70) < 42;
  const wind = earth?.weather.windGusts ?? earth?.weather.windSpeed ?? 0;
  const smoky = (earth?.atmosphere.pm25 ?? 0) >= 35 || (earth?.atmosphere.usAqi ?? 0) >= 151;
  const level = fireAlerts.some((item) => item.severity === "critica")
    ? "critico"
    : fireAlerts.length || (nearest && (nearest.item.confidence ?? 0) >= 0.6) || smoky || (dry && wind >= 35)
      ? "atencion"
      : "normal";
  const title = level === "critico"
    ? "Hay una situación que requiere verificación inmediata"
    : level === "atencion"
      ? "Hay señales para prestar atención"
      : "No aparecen señales cercanas de incendio activo";
  const explanation = nearest
    ? `El satélite marcó un punto caliente a ${nearest.distance.toFixed(1)} km, ${relative(nearest.item.acquired_at)}. Un punto caliente no confirma por sí solo un incendio: debe contrastarse con humo visible, cámaras, drones, brigadistas o autoridades.`
    : dry && wind >= 35
      ? "El suelo está seco y hay viento. No aparece un punto caliente cercano, pero un fuego podría propagarse con rapidez."
      : smoky
        ? "La calidad del aire muestra partículas elevadas. Puede tratarse de humo transportado desde otra zona y requiere contraste con la dirección del viento."
        : "No se registraron puntos calientes cercanos en las últimas 48 horas dentro de las fuentes disponibles.";

  const publicMessage = [
    "🔥 *EcoNexo · Focos de incendio forestal y humo*",
    "",
    `*${title}*`,
    explanation,
    "",
    `📍 ${org?.name || "Área observada"} · ${misionesLocationLabel(center[0], center[1])}`,
    `🛰️ Puntos calientes en 48 h: ${recent.length}`,
    `💨 Viento: ${fmt(earth?.weather.windSpeed, " km/h")} · ráfagas ${fmt(earth?.weather.windGusts, " km/h")}`,
    `💧 Humedad: ${fmt(earth?.weather.humidity, "%")} · suelo ${fmt(earth?.weather.soilMoisture == null ? null : earth.weather.soilMoisture * 100, "%")}`,
    `🌫️ Aire: PM2.5 ${fmt(earth?.atmosphere.pm25, " µg/m³", 1)} · AQI ${fmt(earth?.atmosphere.usAqi)}`,
    "",
    "Si hay fuego o humo visible en Misiones, no te acerques y llamá al 911.",
    "Lectura preventiva. No reemplaza una alerta oficial ni una pericia técnica.",
  ].join("\n");

  async function share(channel: AlertShareInput["channel"]) {
    setSharing(true); setNotice("");
    try {
      const input: AlertShareInput = {
        channel,
        audience: channel === "email" ? "organizacion" : "publico",
        title,
        message: publicMessage,
        module_key: "fire_smoke",
        alert_id: fireAlerts[0]?.id || null,
        metadata: { level, hotspots_48h: recent.length, center },
      };
      await apiPost<AlertShareResult>("/modules/alert-share", token, input);
      const encoded = encodeURIComponent(publicMessage);
      if (channel === "whatsapp") window.open(`https://wa.me/?text=${encoded}`, "_blank", "noopener,noreferrer");
      else if (channel === "telegram") window.open(`https://t.me/share/url?url=&text=${encoded}`, "_blank", "noopener,noreferrer");
      else if (channel === "copiar") await navigator.clipboard.writeText(publicMessage);
      setNotice(channel === "copiar" ? "Mensaje copiado y registrado en auditoría." : "Comunicación registrada. Revisá el contenido antes de enviarlo.");
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : "No se pudo preparar la comunicación.");
    } finally { setSharing(false); }
  }

  return (
    <div className="view fire-module-view">
      <header className="fire-module-header">
        <img src="/brand/econexo-lockup.jpg" alt="EcoNexo" className="fire-brand" />
        <div>
          <span className="eyebrow">MÓDULO LICENCIABLE · LENGUAJE CLARO</span>
          <h2>Focos de incendio forestal y humo</h2>
          <p>Una lectura simple para los 79 municipios de Misiones, brigadas, empresas, medios y comunidades. Separa señales satelitales, condiciones de propagación y humo probable de una confirmación oficial.</p>
        </div>
        <div className={`module-license ${license?.available ? "active" : "inactive"}`}>
          <small>LICENCIA</small><strong>{license?.plan_name || "Sin información"}</strong><span>{license?.status || "no habilitada"}{license?.expires_at ? ` · hasta ${new Date(license.expires_at).toLocaleDateString("es-AR")}` : ""}</span>
        </div>
      </header>

      {!license?.available && <div className="workspace-message error">Este módulo está separado de la licencia principal. Un administrador comercial debe activar o renovar la licencia.</div>}
      {notice && <div className="workspace-message success">{notice}</div>}

      <section className={`plain-fire-status ${level}`}>
        <div className="plain-fire-icon">{level === "normal" ? "✓" : level === "atencion" ? "!" : "‼"}</div>
        <div><span>LECTURA ACTUAL</span><h3>{title}</h3><p>{explanation}</p></div>
        <div className="plain-fire-score"><small>SEÑALES 48 H</small><strong>{recent.length}</strong><span>{fireAlerts.length} alertas abiertas</span></div>
      </section>

      <section className="fire-public-grid">
        <article><small>¿Hay un incendio confirmado?</small><strong>{fireAlerts.some((item) => item.status === "confirmada") ? "Hay una alerta confirmada en la plataforma" : "No con estos datos solamente"}</strong><p>La detección satelital observa calor. La confirmación requiere verificación humana u oficial.</p></article>
        <article><small>¿Puede propagarse rápido?</small><strong>{dry && wind >= 35 ? "Sí, el ambiente favorece propagación" : dry ? "Hay sequedad; vigilar el viento" : "No aparece una combinación extrema"}</strong><p>Se consideran humedad, suelo, viento y lluvia reciente.</p></article>
        <article><small>¿Hay humo que afecte a la gente?</small><strong>{smoky ? "Las partículas están elevadas" : "No aparece una señal fuerte en el modelo"}</strong><p>PM2.5 y AQI son contexto modelado; un sensor local calibrado tiene prioridad.</p></article>
        <article><small>¿Qué hacer?</small><strong>{level === "normal" ? "Mantener vigilancia" : "Verificar sin acercarse al foco"}</strong><p>Ante fuego o humo visible en Misiones: alejarse, no intentar cruzar el frente y llamar al 911.</p></article>
      </section>

      <section className="fire-map-shell">
        <MapView token={token} devices={devices} alerts={fireAlerts} detections={recent.map((entry) => entry.item)} reports={[]} zones={zones.filter((zone) => zone.kind === "incendio" || zone.kind === "general")} center={center} earth={earth} sourceSettings={sourceSettings} initialSatelliteMode="NONE" />
      </section>

      <section className="fire-data-strip">
        <div><small>Humedad</small><strong>{fmt(earth?.weather.humidity, "%")}</strong></div>
        <div><small>Ráfagas</small><strong>{fmt(earth?.weather.windGusts, " km/h")}</strong></div>
        <div><small>PM2.5</small><strong>{fmt(earth?.atmosphere.pm25, " µg/m³", 1)}</strong></div>
        <div><small>AQI</small><strong>{fmt(earth?.atmosphere.usAqi)}</strong></div>
        <div><small>Foco más cercano</small><strong>{nearest ? `${nearest.distance.toFixed(1)} km` : "sin señal"}</strong></div>
      </section>

      <section className="fire-share-card">
        <div><span className="eyebrow">MENSAJE REVISABLE</span><h3>Comunicar sin tecnicismos</h3><p>EcoNexo prepara el texto, pero una persona debe revisarlo antes de enviarlo a medios, organizaciones, laboratorios o la comunidad.</p></div>
        <pre>{publicMessage}</pre>
        <div className="fire-share-actions">
          <button className="primary" disabled={sharing || !license?.available} onClick={() => void share("whatsapp")}>Abrir WhatsApp</button>
          <button disabled={sharing || !license?.available} onClick={() => void share("telegram")}>Abrir Telegram</button>
          <button disabled={sharing || !license?.available} onClick={() => void share("copiar")}>Copiar mensaje</button>
        </div>
      </section>

      <section className="fire-policy-note">
        <strong>Marco operativo provincial</strong>
        <p>El módulo está diseñado para complementar la vigilancia provincial con cámaras y torres, drones, análisis satelital, sensores y verificación territorial. No atribuye carácter oficial a una señal automática ni sustituye la actuación del Ministerio de Ecología, Policía, Bomberos, Defensa Civil o autoridades municipales.</p>
      </section>
    </div>
  );
}
