import { LegalPage, LegalSection } from "../../components/LegalPage";

export const metadata = { title: "Metodología y fuentes" };

export default function MethodologyPage() {
  return (
    <LegalPage
      title="Metodología, fuentes y alcance territorial"
      subtitle="Cómo EcoNexo transforma observaciones de Misiones en señales revisables, alertas e informes técnicos."
    >
      <LegalSection number="01" title="Alcance territorial">
        <p>EcoNexo opera con alcance provincial en Misiones: 17 departamentos y 79 municipios. Las coordenadas se validan antes de incorporarse a mapas, indicadores, alertas e informes. La geometría productiva se sincroniza desde GeoRef Argentina; el polígono incluido en el proyecto funciona únicamente como respaldo operativo.</p>
      </LegalSection>
      <LegalSection number="02" title="Jerarquía de evidencia">
        <p>La plataforma distingue medición física, modelado meteorológico, proxy satelital, reporte comunitario y verificación institucional. Ninguna señal automática se presenta como constatación oficial. Un punto caliente satelital requiere contraste con humo visible, cámaras, drones, brigadas, sensores o autoridad competente.</p>
      </LegalSection>
      <LegalSection number="03" title="Fuentes principales">
        <ul>
          <li>Nodos IoT y lecturas persistidas por organización.</li>
          <li>Open-Meteo para contexto meteorológico, calidad del aire y contexto hídrico.</li>
          <li>NASA FIRMS para señales térmicas, únicamente cuando existe una credencial productiva.</li>
          <li>GeoRef Argentina para normalización y geometría territorial.</li>
          <li>Reportes comunitarios con consentimiento, ubicación y moderación.</li>
          <li>Datos de laboratorios y organismos incorporados con trazabilidad de muestra y protocolo.</li>
        </ul>
      </LegalSection>
      <LegalSection number="04" title="Cálculos SpaceAI">
        <p><strong>Excedencia relativa (%)</strong> = valor observado / valor de referencia × 100.</p>
        <p><strong>Score por indicador</strong> = severidad × persistencia × confiabilidad.</p>
        <p><strong>HTI</strong> = Σ(peso × score × vulnerabilidad poblacional) / Σ(pesos).</p>
        <p>Los indicadores categóricos o no lineales —AQI, índice UV, SPI, ruido, IDLH e índice de calor— se interpretan con su escala específica y no mediante una equivalencia porcentual directa.</p>
      </LegalSection>
      <LegalSection number="05" title="Escala de comunicación">
        <p>R0 basal, R1 vigilancia, R2 alerta, R3 amenaza alta, R4 crítico y R5 emergencia. Las comunicaciones R3-R5 requieren revisión humana y deben identificar fuente, hora de corte, territorio, incertidumbre y responsable de aprobación.</p>
      </LegalSection>
      <LegalSection number="06" title="Incendios y humo en Misiones">
        <p>El módulo se alinea con el Sistema Federal de Manejo del Fuego, el Plan Provincial de Manejo del Fuego y el esquema provincial de alerta temprana. EcoNexo complementa la gestión: no reemplaza al 911, a Bomberos, a Defensa Civil, al Ministerio de Ecología ni a los protocolos de la organización contratante.</p>
      </LegalSection>
      <LegalSection number="07" title="Limitaciones y revisión">
        <p>Los resultados dependen de cobertura, latencia, calibración, resolución espacial, nubosidad, calidad de sensores y disponibilidad de fuentes. Antes de automatizar comunicaciones públicas, cada organización debe aprobar sus umbrales, responsables, canales, retención de evidencia y protocolo de escalamiento.</p>
      </LegalSection>
    </LegalPage>
  );
}
