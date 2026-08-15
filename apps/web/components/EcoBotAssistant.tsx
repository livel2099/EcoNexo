"use client";

import { useEffect, useMemo, useRef, useState } from "react";

/**
 * EcoBot — asistente de ayuda de EcoNexo.
 *
 * Widget flotante disponible en toda la plataforma. Responde consultas sobre
 * los módulos, el reporte ciudadano, las alertas y los informes usando una
 * base de conocimiento curada (sin costo, sin llamadas externas, funciona
 * offline).
 *
 * Preparado para IA: `resolveAnswer` es el único punto de resolución. Cuando
 * exista un backend con LLM, basta con activar `NEXT_PUBLIC_ECOBOT_LLM=true`
 * e implementar el POST a `/assistant/chat`; el resto del widget no cambia.
 */

type Reply = { text: string; suggestions?: string[] };
type Message = { id: number; from: "bot" | "user"; text: string };

interface KnowledgeEntry {
  id: string;
  keywords: string[];
  answer: string;
  suggestions?: string[];
}

const STARTERS = [
  "¿Qué es EcoNexo?",
  "¿Cómo reporto un incendio?",
  "¿Qué significan los niveles R0 a R5?",
  "¿Cómo genero un informe?",
];

const KNOWLEDGE: KnowledgeEntry[] = [
  {
    id: "que-es",
    keywords: ["que es", "econexo", "para que sirve", "de que se trata", "plataforma", "que hace"],
    answer:
      "EcoNexo es una plataforma de inteligencia ambiental que detecta, correlaciona y documenta incidentes antes de que escalen. Integra sensores IoT, observación satelital (NASA FIRMS, Copernicus), meteorología y reportes ciudadanos para producir alertas priorizadas, trazabilidad e informes institucionales. Esta edición está enfocada en Misiones: 17 departamentos y 79 municipios.",
    suggestions: ["¿Qué módulos tiene?", "¿Cómo empiezo a usarlo?"],
  },
  {
    id: "modulos",
    keywords: ["modulos", "modulo", "secciones", "que tiene", "funciones", "menu", "navegacion"],
    answer:
      "Los módulos principales son: Centro de Comando (mapa y alertas), Fuego y humo, Plagas forestales, Alerta IA (Observatorio SpaceAI), Dispositivos, Reglas, Reportes ciudadanos, Informes y —solo para administradores— Admin Core. Algunos son licenciables según tu plan.",
    suggestions: ["¿Qué es el Centro de Comando?", "¿Qué es Alerta IA?"],
  },
  {
    id: "reportar",
    keywords: ["reportar", "reporte", "denunciar", "incendio", "humo", "aviso", "como reporto", "reporte ciudadano", "vecino"],
    answer:
      "Para enviar un reporte ciudadano entrá a /reportar y: 1) elegí el territorio u organización, 2) el tipo de incidente (humo, incendio, inundación, vertido u otro), 3) describí qué observás, 4) adjuntá una foto opcional (máx. 8 MB), 5) compartí tu ubicación (debe estar en Misiones), 6) aceptá el tratamiento de datos y enviá. Tu reporte se cruza con sensores y satélite para su validación.",
    suggestions: ["¿Necesito una cuenta para reportar?", "¿Es un canal de emergencias?"],
  },
  {
    id: "emergencia",
    keywords: ["emergencia", "911", "urgente", "peligro", "fuego ahora", "riesgo"],
    answer:
      "⚠️ EcoNexo NO es un canal de emergencias. Ante fuego, humo o riesgo inmediato para personas o bienes, alejate del peligro y llamá al 911. La plataforma es una herramienta de detección temprana y decisión, no de respuesta de emergencia.",
  },
  {
    id: "alertas",
    keywords: ["alerta", "alertas", "confirmar", "descartar", "escalar", "severidad", "prioridad"],
    answer:
      "Las alertas aparecen priorizadas a la derecha del Centro de Comando, con su severidad, porcentaje de confianza y las fuentes que las sustentan. Sobre cada una podés: Confirmar (validás que es real), Descartar (falso positivo) o Escalar (la elevás a una instancia superior). Cada acción queda registrada para trazabilidad.",
    suggestions: ["¿Qué es la confianza de una alerta?", "¿Qué son las reglas?"],
  },
  {
    id: "confianza",
    keywords: ["confianza", "porcentaje", "precision", "que tan real"],
    answer:
      "La confianza es un porcentaje (0–100%) que estima cuán probable es que una alerta sea real. En las tarjetas se colorea: verde si es ≥85%, amarillo si es ≥60% y gris por debajo. La severidad, en cambio, clasifica la gravedad del incidente.",
  },
  {
    id: "niveles",
    keywords: ["r0", "r5", "niveles", "hti", "amenaza", "health threat", "escala", "r3", "r4"],
    answer:
      "El Health Threat Index (HTI) va de R0 a R5: R0 sin amenaza, R1 baja, R2 moderada, R3 elevada (umbral típico de alerta operativa), R4 alta y R5 crítica. El administrador define desde qué nivel (por defecto R3) se activan alertas operativas automáticas.",
    suggestions: ["¿Qué es Alerta IA?"],
  },
  {
    id: "alerta-ia",
    keywords: ["alerta ia", "spaceai", "observatorio", "inteligencia artificial", "ia", "gemelo digital"],
    answer:
      "Alerta IA (Observatorio SpaceAI) reúne el análisis asistido por IA: telemetría por dispositivo, contexto de Open-Meteo (clima), CAMS (aerosoles) y GloFAS (crecidas), focos NASA FIRMS, un gemelo digital del territorio, mensajes revisables y el índice de amenaza R0–R5.",
    suggestions: ["¿Qué significan los niveles R0 a R5?"],
  },
  {
    id: "fuego",
    keywords: ["fuego", "humo", "incendios", "focos", "firms", "termico"],
    answer:
      "El módulo Fuego y humo combina un mapa nítido de focos térmicos, contexto meteorológico (viento, temperatura, humedad) y registro de comunicaciones. Importante: la evidencia satelital es un indicio, no una confirmación oficial de incendio; eso corresponde a los organismos competentes.",
  },
  {
    id: "plagas",
    keywords: ["plaga", "plagas", "forestal", "sanidad", "ndvi", "arboles", "fitosanitario"],
    answer:
      "El módulo Plagas forestales (sanidad forestal del norte, para San Antonio y General Manuel Belgrano) integra contexto meteorológico, índices satelitales NDVI y humedad, recorridas, trampas y reportes. Aporta contexto y trazabilidad, pero no confirma ni identifica una plaga por sí mismo.",
  },
  {
    id: "dispositivos",
    keywords: ["dispositivo", "dispositivos", "sensor", "sensores", "nodo", "nodos", "esp32", "telemetria"],
    answer:
      "En Dispositivos ves el inventario de sensores (nodos) de tu organización: identificador, ubicación, última telemetría y cuáles están en línea. Los nodos ESP32 publican datos por el bus MQTT y aparecen en tiempo real en el mapa.",
  },
  {
    id: "reglas",
    keywords: ["regla", "reglas", "automatizar", "automatico", "condicion", "umbral"],
    answer:
      "Las reglas automatizan la generación y elevación de alertas. Definís una condición (por ejemplo, humo sobre cierto umbral, o foco satelital + reporte ciudadano en la misma zona) y cuando se cumple, se dispara o eleva una alerta sin intervención manual.",
  },
  {
    id: "informes",
    keywords: ["informe", "informes", "reporte institucional", "pdf", "csv", "exportar", "documento"],
    answer:
      "En Informes generás documentos formales: 1) elegí período y destinatario (organización, municipio, PO, inversor, aseguradora o auditoría), 2) se consolidan dispositivos, alertas, severidad, tiempos y reportes, 3) agregás resumen y recomendaciones, 4) exportás a PDF, CSV o email, 5) opcionalmente compartís un enlace público revocable. Nota: los informes no equivalen a una certificación independiente.",
    suggestions: ["¿Cómo exporto a PDF?"],
  },
  {
    id: "pdf",
    keywords: ["exportar pdf", "guardar pdf", "imprimir", "como exporto"],
    answer:
      "Para exportar a PDF, usá la opción imprimir/guardar del informe (o Ctrl+P en el navegador) y elegí destino «Guardar como PDF». Activá «Gráficos de fondo» para conservar los colores.",
  },
  {
    id: "login",
    keywords: ["login", "ingresar", "iniciar sesion", "crear organizacion", "registro", "registrarme", "cuenta", "contraseña", "password"],
    answer:
      "Para empezar, en la pantalla de acceso elegí «Crear organización» (el primer usuario queda como administrador): completá organización, localidad en Misiones, tipo de operación, tu nombre, email y contraseña (mín. 8 caracteres, una letra y un número) y aceptá los términos. Si ya tenés cuenta, usá «Ingresar». Google es opcional si el administrador lo configuró.",
    suggestions: ["Olvidé mi contraseña", "¿Qué es el Admin Core?"],
  },
  {
    id: "password-reset",
    keywords: ["olvide", "recuperar contraseña", "resetear", "no puedo entrar", "perdi la clave"],
    answer:
      "Si olvidaste tu contraseña, contactá al administrador de tu organización para que gestione el restablecimiento desde Admin Core.",
  },
  {
    id: "admin",
    keywords: ["admin", "administrador", "abm", "usuarios", "roles", "geocerca", "auditoria", "permisos"],
    answer:
      "Admin Core (solo administradores) permite gestionar usuarios y roles, datos de la organización, geocercas PostGIS, fuentes ambientales/SpaceAI, dispositivos, reglas y auditoría. También incluye la bandeja Mensajes, que registra cada inicio de sesión con su contexto e IP anonimizada.",
  },
  {
    id: "planes",
    keywords: ["plan", "planes", "suscripcion", "suscripciones", "precio", "licencia", "modulo licenciable", "enterprise"],
    answer:
      "Los planes van de menor a mayor alcance: Sandbox, Diagnóstico, Piloto, Municipal, Provincia/Pro, Enterprise y Academia. Cada suscripción gestiona solicitud, aprobación, vencimiento, consumo y módulos habilitados. Módulos como Fuego y humo o Plagas forestales pueden requerir plan.",
  },
  {
    id: "cuenta-reportar",
    keywords: ["necesito cuenta", "sin cuenta", "registrarme para reportar", "anonimo"],
    answer:
      "No necesitás cuenta para enviar un reporte ciudadano: la página /reportar es pública. Solo se pide tu consentimiento y una ubicación dentro de Misiones. La cuenta es para operadores y administradores de una organización.",
  },
  {
    id: "misiones",
    keywords: ["misiones", "territorio", "fuera de", "no aparece", "limite", "departamentos"],
    answer:
      "Esta edición está restringida a la provincia de Misiones (17 departamentos, 79 municipios). Las señales o reportes fuera de ese límite se excluyen del centro de comando de forma intencional; no es un error.",
  },
  {
    id: "kpis",
    keywords: ["kpi", "kpis", "indicador", "indicadores", "metricas", "objetivos"],
    answer:
      "Los 4 indicadores de la barra superior son: Tiempo de detección (objetivo <5 min), Precisión del motor IA (85%+), Reportes válidos (70%+) y Reducción de respuesta (-40%). Se pintan en verde cuando cumplen el objetivo y en amarillo cuando aún no.",
  },
  {
    id: "movil",
    keywords: ["movil", "celular", "app", "android", "ios", "telefono", "aplicacion"],
    answer:
      "EcoNexo tiene una app móvil nativa (Expo + React Native) para Android e iOS, con Inicio, Fuego y Humo, Alerta IA, reportes con foto/ubicación y tu cuenta. Usás las mismas credenciales que en la web.",
  },
];

const GREETING =
  "¡Hola! Soy EcoBot, tu asistente de EcoNexo 🌱 Puedo ayudarte con los módulos, cómo reportar, las alertas, los informes y más. ¿En qué te ayudo?";

const FALLBACK =
  "No estoy seguro de eso todavía. Puedo ayudarte con: qué es EcoNexo, cómo reportar, alertas, niveles R0–R5, informes, dispositivos, reglas, planes o acceso. Para casos puntuales, escribí a tu administrador o consultá el manual de usuario.";

function normalize(value: string): string {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/[¿?¡!.,;:]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function matchKnowledge(query: string): Reply {
  const q = normalize(query);
  if (!q) return { text: FALLBACK };

  let best: KnowledgeEntry | null = null;
  let bestScore = 0;
  for (const entry of KNOWLEDGE) {
    let score = 0;
    for (const keyword of entry.keywords) {
      const k = normalize(keyword);
      if (!k) continue;
      // Frases (con espacio) pesan más que palabras sueltas.
      if (q.includes(k)) score += k.includes(" ") ? 3 : 1;
    }
    if (score > bestScore) {
      bestScore = score;
      best = entry;
    }
  }

  if (!best || bestScore === 0) return { text: FALLBACK };
  return { text: best.answer, suggestions: best.suggestions };
}

/**
 * Punto único de resolución de respuestas. Hoy usa la base de conocimiento
 * local. Para activar un LLM en el futuro: implementar el POST a
 * `/assistant/chat` cuando `NEXT_PUBLIC_ECOBOT_LLM === "true"`.
 */
async function resolveAnswer(query: string): Promise<Reply> {
  return matchKnowledge(query);
}

export default function EcoBotAssistant() {
  const [open, setOpen] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([{ id: 0, from: "bot", text: GREETING }]);
  const [suggestions, setSuggestions] = useState<string[]>(STARTERS);
  const nextId = useRef(1);
  const logRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const hasConversation = useMemo(() => messages.length > 1, [messages.length]);

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight;
  }, [messages, thinking]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  async function send(raw: string) {
    const text = raw.trim();
    if (!text || thinking) return;
    const userMsg: Message = { id: nextId.current++, from: "user", text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setSuggestions([]);
    setThinking(true);

    const reply = await resolveAnswer(text);
    // Pequeña demora para una sensación natural de respuesta.
    window.setTimeout(() => {
      setMessages((prev) => [...prev, { id: nextId.current++, from: "bot", text: reply.text }]);
      setSuggestions(reply.suggestions ?? []);
      setThinking(false);
    }, 320);
  }

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    void send(input);
  }

  function onKeyDown(event: React.KeyboardEvent) {
    if (event.key === "Escape") setOpen(false);
  }

  return (
    <div className="ecobot no-print" onKeyDown={onKeyDown}>
      {open && (
        <section className="ecobot-panel" role="dialog" aria-label="EcoBot, asistente de EcoNexo">
          <header className="ecobot-head">
            <span className="ecobot-avatar" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="2.3" /><path d="M12 2v4M12 18v4M2 12h4M18 12h4M5 5l2.4 2.4M16.6 16.6 19 19M19 5l-2.4 2.4M7.4 16.6 5 19" />
              </svg>
            </span>
            <div className="ecobot-head-text">
              <strong>EcoBot</strong>
              <small><i /> Asistente en línea</small>
            </div>
            <button type="button" className="ecobot-close" onClick={() => setOpen(false)} aria-label="Cerrar asistente">✕</button>
          </header>

          <div className="ecobot-log" ref={logRef} aria-live="polite">
            {messages.map((message) => (
              <div key={message.id} className={`ecobot-msg ${message.from}`}>
                {message.text}
              </div>
            ))}
            {thinking && (
              <div className="ecobot-msg bot ecobot-typing" aria-label="EcoBot está escribiendo">
                <span /><span /><span />
              </div>
            )}
          </div>

          {suggestions.length > 0 && (
            <div className="ecobot-chips">
              {suggestions.map((chip) => (
                <button key={chip} type="button" className="ecobot-chip" onClick={() => void send(chip)}>{chip}</button>
              ))}
            </div>
          )}

          <form className="ecobot-input" onSubmit={onSubmit}>
            <input
              ref={inputRef}
              value={input}
              onChange={(event) => setInput(event.target.value)}
              placeholder="Escribí tu consulta…"
              aria-label="Escribí tu consulta para EcoBot"
              maxLength={300}
            />
            <button type="submit" className="ecobot-send" disabled={!input.trim() || thinking} aria-label="Enviar">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m22 2-7 20-4-9-9-4Z" /><path d="M22 2 11 13" /></svg>
            </button>
          </form>
          <p className="ecobot-disclaimer">EcoBot orienta sobre el uso de EcoNexo. No es un canal de emergencias — ante riesgo, llamá al 911.</p>
        </section>
      )}

      <button
        type="button"
        className={`ecobot-fab ${open ? "is-open" : ""}`}
        onClick={() => setOpen((value) => !value)}
        aria-label={open ? "Cerrar asistente EcoBot" : "Abrir asistente EcoBot"}
        aria-expanded={open}
      >
        {open ? (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M18 6 6 18M6 6l12 12" /></svg>
        ) : (
          <>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round"><path d="M7.9 20A9 9 0 1 0 4 16.1L3 21l4.9-1Z" /><circle cx="9" cy="12" r="1" fill="currentColor" stroke="none" /><circle cx="12" cy="12" r="1" fill="currentColor" stroke="none" /><circle cx="15" cy="12" r="1" fill="currentColor" stroke="none" /></svg>
            {!hasConversation && <span className="ecobot-fab-label">¿Ayuda?</span>}
          </>
        )}
      </button>
    </div>
  );
}
