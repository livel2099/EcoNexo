"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import { apiGet } from "../app/lib/api";
import { fetchEarthIntel, type EarthIntel } from "../app/lib/earth-intel";
import type { Alert, Detection, Device, EnvironmentalSourceSettings, ModuleEntitlement } from "../app/lib/types";

const MapView = dynamic(() => import("./MapView"), { ssr: false });
const SAN_ANTONIO: [number, number] = [-26.01709, -53.78987];
const BERNARDO_DE_IRIGOYEN: [number, number] = [-26.2552, -53.6478];

function distanceKm(a: [number, number], b: [number, number]): number {
  const r = 6371;
  const toRad = (value: number) => value * Math.PI / 180;
  const dLat = toRad(b[0] - a[0]);
  const dLon = toRad(b[1] - a[1]);
  const x = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a[0])) * Math.cos(toRad(b[0])) * Math.sin(dLon / 2) ** 2;
  return r * 2 * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
}

function clamp(value: number): number {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function fmt(value: number | null | undefined, suffix = "", digits = 0): string {
  return value == null || !Number.isFinite(value) ? "s/d" : `${value.toFixed(digits)}${suffix}`;
}

export default function ForestryPestPanel({
  token,
  devices,
  alerts,
  detections,
  sourceSettings,
}: {
  token: string;
  devices: Device[];
  alerts: Alert[];
  detections: Detection[];
  sourceSettings: EnvironmentalSourceSettings;
}) {
  const [modules, setModules] = useState<ModuleEntitlement[]>([]);
  const [intel, setIntel] = useState<EarthIntel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    void apiGet<ModuleEntitlement[]>("/modules/me", token).then(setModules).catch(() => setModules([]));
  }, [token]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    void fetchEarthIntel(SAN_ANTONIO[0], SAN_ANTONIO[1], undefined, false, {
      weatherEnabled: sourceSettings.open_meteo_enabled,
      airQualityEnabled: sourceSettings.air_quality_enabled,
      floodEnabled: false,
      cacheTtlMinutes: sourceSettings.refresh_minutes,
    }).then((value) => { if (active) setIntel(value); })
      .catch((cause) => { if (active) setError(cause instanceof Error ? cause.message : "No se pudo obtener el contexto ambiental"); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [sourceSettings.air_quality_enabled, sourceSettings.open_meteo_enabled, sourceSettings.refresh_minutes]);

  const license = modules.find((item) => item.module_key === "forestry_pests");
  const radarDistance = distanceKm(SAN_ANTONIO, BERNARDO_DE_IRIGOYEN);
  const screening = useMemo(() => {
    const temperature = intel?.weather.temperature ?? 22;
    const humidity = intel?.weather.humidity ?? 70;
    const precipitation = intel?.weather.precipitation ?? 0;
    const soil = (intel?.weather.soilMoisture ?? 0.25) * 100;
    const gusts = intel?.weather.windGusts ?? intel?.weather.windSpeed ?? 0;
    const heatMoisture = clamp((temperature >= 24 && temperature <= 32 ? 35 : 15) + (humidity >= 65 ? 30 : 12) + (precipitation > 0 ? 15 : 5) + (soil >= 25 ? 15 : 5));
    const stress = clamp((temperature >= 30 ? 28 : 10) + (humidity < 45 ? 28 : 8) + (soil < 18 ? 30 : 8) + (gusts >= 35 ? 14 : 5));
    const flightContext = clamp((temperature >= 18 && temperature <= 31 ? 35 : 12) + (humidity >= 50 && humidity <= 85 ? 25 : 10) + (gusts < 25 ? 30 : gusts < 40 ? 15 : 5) + (precipitation === 0 ? 10 : 2));
    const overall = Math.round((heatMoisture * 0.4) + (stress * 0.35) + (flightContext * 0.25));
    return { heatMoisture, stress, flightContext, overall };
  }, [intel]);
  const level = screening.overall >= 70 ? "alto" : screening.overall >= 45 ? "medio" : "bajo";

  return (
    <div className="view forestry-pest-view">
      <header className="forestry-pest-header">
        <div>
          <span className="eyebrow">MÓDULO LICENCIABLE · NORTE DE MISIONES</span>
          <h2>Vigilancia preventiva de plagas forestales</h2>
          <p>San Antonio y el corredor de General Manuel Belgrano. Combina clima, estrés de la plantación, recorridas, trampas y denuncias. No diagnostica una plaga solamente con radar o satélite.</p>
        </div>
        <div className={`module-license ${license?.available ? "active" : "inactive"}`}><small>LICENCIA</small><strong>{license?.plan_name || "Sin información"}</strong><span>{license?.status || "no habilitada"}</span></div>
      </header>

      {!license?.available && <div className="workspace-message error">El módulo de sanidad forestal está separado de la licencia principal.</div>}
      {error && <div className="workspace-message error">{error}</div>}

      <section className={`pest-screening ${level}`}>
        <div><span>LECTURA PREVENTIVA</span><h3>Condiciones ambientales: {level}</h3><p>Es una priorización para decidir dónde recorrer y colocar trampas. La confirmación debe realizarse por inspección fitosanitaria y, cuando corresponda, laboratorio.</p></div>
        <strong>{loading ? "…" : screening.overall}<small>/100</small></strong>
      </section>

      <section className="pest-metric-grid">
        <article><small>Ambiente cálido y húmedo</small><strong>{loading ? "—" : screening.heatMoisture}</strong><p>Ayuda a priorizar hongos, patógenos y daños asociados a exceso de humedad.</p></article>
        <article><small>Estrés de la forestación</small><strong>{loading ? "—" : screening.stress}</strong><p>Sequedad, calor y viento pueden debilitar árboles y volver más visible el daño.</p></article>
        <article><small>Ventana de vuelo</small><strong>{loading ? "—" : screening.flightContext}</strong><p>Contexto climático para reforzar trampas y recorridas; no identifica insectos.</p></article>
        <article><small>Radar cercano</small><strong>{radarDistance.toFixed(0)} km</strong><p>Distancia aproximada entre localidades. No representa la ubicación exacta de la antena.</p></article>
      </section>

      <section className="pest-map-shell">
        <MapView devices={devices} alerts={alerts} detections={detections} reports={[]} center={SAN_ANTONIO} earth={intel} sourceSettings={sourceSettings} showForestryAssets initialSatelliteMode={sourceSettings.copernicus_enabled ? "NDVI" : "NONE"} />
      </section>

      <section className="pest-data-strip">
        <div><small>Temperatura</small><strong>{fmt(intel?.weather.temperature, " °C", 1)}</strong></div>
        <div><small>Humedad</small><strong>{fmt(intel?.weather.humidity, "%")}</strong></div>
        <div><small>Humedad del suelo</small><strong>{fmt(intel?.weather.soilMoisture == null ? null : intel.weather.soilMoisture * 100, "%")}</strong></div>
        <div><small>Ráfagas</small><strong>{fmt(intel?.weather.windGusts, " km/h")}</strong></div>
        <div><small>NDVI Copernicus</small><strong>{sourceSettings.copernicus_enabled && sourceSettings.copernicus_configured ? "disponible" : "pendiente"}</strong></div>
      </section>

      <section className="pest-watch-grid">
        <article><span>PINOS</span><h3>Avispa barrenadora</h3><p>Buscar resinación, perforaciones redondas, aserrín fino, copa amarillenta o árboles debilitados. Una fotografía no reemplaza la identificación de la muestra.</p></article>
        <article><span>PINOS</span><h3>Gorgojos y escolítidos</h3><p>Observar galerías bajo corteza, polvo de madera, decaimiento por manchones y asociación con estrés hídrico o daño previo.</p></article>
        <article><span>EUCALIPTOS</span><h3>Chinches y avispas de agallas</h3><p>Registrar bronceado de hojas, defoliación, deformaciones o agallas en brotes y hojas jóvenes.</p></article>
        <article><span>FRONTERA</span><h3>Hallazgo inusual</h3><p>No mover madera ni insectos sin indicación. Georreferenciar, aislar la muestra y escalar a especialistas para evitar dispersión.</p></article>
      </section>

      <section className="pest-action-grid">
        <article><span>1</span><div><h3>Recorrer y fotografiar</h3><p>Registrar decaimiento, perforaciones, aserrín, resinación, muerte de ramas, cancros y cambios de copa.</p></div></article>
        <article><span>2</span><div><h3>Georreferenciar</h3><p>Marcar lote, especie forestal, edad aproximada, superficie afectada y fecha de observación.</p></div></article>
        <article><span>3</span><div><h3>Usar trampas y muestras</h3><p>La captura o muestra debe conservar identificación del sitio y cadena de remisión.</p></div></article>
        <article><span>4</span><div><h3>Escalar la sospecha</h3><p>Derivar a referentes fitosanitarios, SENASA o laboratorio. EcoNexo mantiene la trazabilidad del reporte.</p></div></article>
      </section>

      <section className="pest-network-grid">
        <article><small>VIGILANCIA OFICIAL</small><h3>SENASA / SINAVIMO</h3><p>Canal para reportes verificados, situación de plagas y vigilancia fitosanitaria reconocida oficialmente.</p><a href="https://www.argentina.gob.ar/senasa/programas-sanitarios/cadenavegetal/forestales-embalajes/forestales-produccion-primaria/plagas" target="_blank" rel="noreferrer">Consultar vigilancia</a></article>
        <article><small>DIAGNÓSTICO REGIONAL</small><h3>FCF UNaM · Eldorado</h3><p>Laboratorio de Protección Forestal especializado en problemas sanitarios de Pinus y Eucalyptus en Misiones.</p><a href="https://www.argentina.gob.ar/sanidad-forestal" target="_blank" rel="noreferrer">Ver red de laboratorios</a></article>
        <article><small>MANEJO INTEGRADO</small><h3>INTA Montecarlo</h3><p>Referencia regional en protección forestal y biocontrol de la avispa barrenadora de los pinos.</p><a href="https://intainforma.inta.gob.ar/biocontrolador-para-el-manejo-de-la-principal-plaga-de-pinos-adultos/" target="_blank" rel="noreferrer">Ver información técnica</a></article>
      </section>

      <section className="pest-radar-note">
        <div><span className="eyebrow">RADAR SINARAME</span><h3>Qué puede aportar y qué no</h3></div>
        <p>El radar meteorológico de Bernardo de Irigoyen puede mostrar precipitación, tormentas y ecos atmosféricos regionales. El punto del mapa es una referencia municipal, no la ubicación exacta de la antena. Incluso puede registrar concentraciones de partículas o insectos, pero una imagen de radar no determina especie, presencia de Sirex, escolítidos ni daño sanitario en un lote. Por eso EcoNexo lo usa solo como contexto para programar recorridas.</p>
        <div className="pest-links">
          <a href="https://ws2.smn.gob.ar/radar" target="_blank" rel="noreferrer">Abrir radares del SMN</a>
          <a href="https://www.argentina.gob.ar/senasa/programas-sanitarios/cadenavegetal/forestales-embalajes/forestales-produccion-primaria/plagas" target="_blank" rel="noreferrer">Vigilancia de plagas SENASA</a>
        </div>
      </section>
    </div>
  );
}
