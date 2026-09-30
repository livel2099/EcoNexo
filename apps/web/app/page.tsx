import Link from "next/link";
import SiteFooter from "../components/SiteFooter";
import LandingLogo, { RegisteredWordmark } from "../components/LandingLogo";
import styles from "./home.module.css";

const modules = [
  ["01", "Centro de Comando", "El territorio, en una sola vista.", "Mapas, dispositivos, señales ambientales y alertas para acompañar la operación de tu organización."],
  ["02", "SpaceAI · Alerta IA", "Datos que ayudan a decidir.", "Indicadores ambientales con contexto meteorológico, nivel de amenaza y evidencia para revisión humana."],
  ["03", "Fuego, humo y sanidad forestal", "Observar. Contrastar. Actuar.", "Señales térmicas y observación satelital para orientar la vigilancia de incendios y anomalías forestales."],
  ["04", "EcoNexo AG + EcoCampo", "Inteligencia para el campo.", "Seguimiento de lotes, vegetación, aptitud agropecuaria y estimaciones productivas con contexto territorial."],
  ["05", "Reportes e informes", "De la observación a la evidencia.", "Reportes ciudadanos, validación institucional e informes que conservan fuentes, ubicación y metodología."],
  ["06", "Admin Core", "Tu organización, bajo control.", "Administración de usuarios, fuentes, geocercas y suscripción. Disponible para administradores de la organización."],
];

export default function Home() {
  return <div className={styles.page}>
    <a className={styles.skip} href="#contenido">Saltar al contenido</a>
    <header className={styles.header}>
      <Link href="/" className={styles.brand} aria-label="EcoNexo, marca registrada · inicio"><RegisteredWordmark /></Link>
      <nav aria-label="Navegación de la portada"><a href="#plataforma">Plataforma</a><a href="#flujo">Cómo funciona</a><a href="#documentacion">Documentación</a><a href="#contacto">Contacto</a></nav>
      <Link href="/login" className={styles.access}>Acceder <span aria-hidden="true">↗</span></Link>
    </header>
    <main id="contenido">
      <section className={styles.hero}>
        <div className={styles.heroCopy}>
          <span className={styles.eyebrow}><i /> INTELIGENCIA BIOCLIMÁTICA ACTIVA</span>
          <h1>Conectamos datos.<br />Activamos <em>decisiones.</em></h1>
          <p>Tu territorio genera señales. EcoNexo integra sensores, observación satelital y reportes ciudadanos para entender qué está pasando y decidir cómo actuar.</p>
          <div className={styles.buttons}><Link href="/login" className={styles.primary}>Acceder a la plataforma <span aria-hidden="true">↗</span></Link><a href="#flujo" className={styles.secondary}>Explorar el flujo <span aria-hidden="true">↓</span></a></div>
          <div className={styles.heroNote}>Desarrollado en Argentina <span>·</span> Foco territorial en Misiones</div>
        </div>
        <LandingLogo />
      </section>
      <div className={styles.audience}><span>PENSADO PARA</span><strong>Municipios</strong><strong>Organizaciones forestales</strong><strong>Sector productivo</strong><strong>Investigación</strong></div>
      <section id="plataforma" className={styles.section}>
        <div className={styles.sectionTitle}><span className={styles.eyebrow}>01 / LA PLATAFORMA</span><h2>Del dato disperso<br />a una visión compartida.</h2><p>Un espacio de trabajo para observar el ambiente, organizar la respuesta y documentar lo que sucede. Los módulos operativos se habilitan según la licencia de cada organización.</p></div>
        <div className={styles.moduleGrid}>{modules.map(([number, title, subtitle, description]) => <article key={number}><span className={styles.number}>{number} <span aria-hidden="true">↗</span></span><h3>{title}</h3><strong>{subtitle}</strong><p>{description}</p></article>)}</div>
      </section>
      <section id="flujo" className={`${styles.section} ${styles.flow}`}>
        <div className={styles.sectionTitle}><span className={styles.eyebrow}>02 / CÓMO FUNCIONA</span><h2>Una señal es el comienzo.<br />La acción es el objetivo.</h2></div>
        <ol className={styles.steps}>{[
          ["Conectar", "Configurá tu territorio y las fuentes disponibles: nodos IoT, meteorología, satélites y reportes ciudadanos."],
          ["Interpretar", "Consultá el mapa y los indicadores. Contrastá ubicación, actualidad, origen y confiabilidad de cada señal."],
          ["Validar y actuar", "Revisá las alertas con tu equipo, confirmá los eventos y coordiná la respuesta según tus protocolos."],
          ["Documentar", "Registrá las acciones y generá informes con evidencia para dar seguimiento y mejorar las decisiones."],
        ].map(([title, body], index) => <li key={title}><span>0{index + 1}</span><h3>{title}</h3><p>{body}</p></li>)}</ol>
        <p className={styles.flowNote}>La decisión conserva un responsable humano. Las señales automáticas requieren validación y dependen de la cobertura y disponibilidad de las fuentes.</p>
      </section>
      <section id="documentacion" className={styles.section}>
        <div className={styles.sectionTitle}><span className={styles.eyebrow}>03 / DOCUMENTACIÓN</span><h2>Conocé el sistema.<br />Trabajá con contexto.</h2><p>Guías abiertas para entender el recorrido, las fuentes y el alcance de la plataforma.</p></div>
        <div className={styles.docs}>
          <Link href="/documentacion"><span>GUÍA DE USO</span><h3>Primeros pasos <b aria-hidden="true">↗</b></h3><p>Desde la solicitud de acceso hasta la configuración del equipo y el seguimiento de alertas.</p></Link>
          <Link href="/metodologia"><span>FUENTES Y CRITERIOS</span><h3>Metodología <b aria-hidden="true">↗</b></h3><p>Origen de los datos, interpretación de indicadores, validación y límites de la información.</p></Link>
          <Link href="/seguridad"><span>ORGANIZACIÓN Y ACCESO</span><h3>Seguridad <b aria-hidden="true">↗</b></h3><p>Roles, separación de datos por organización y prácticas de protección de la plataforma.</p></Link>
        </div>
      </section>
      <section className={`${styles.section} ${styles.community}`}><div><span className={styles.eyebrow}>CONOCIMIENTO QUE SE COMPARTE</span><h2>El territorio también<br />se entiende en comunidad.</h2><p>EcoNexoFoI es la red gratuita de investigación. Explorá el intercambio de conocimiento ambiental o aportá una observación desde el canal de reportes ciudadanos.</p></div><div className={styles.buttons}><Link href="/red-investigacion" className={styles.secondary}>Explorar EcoNexoFoI ↗</Link><Link href="/reportar" className={styles.secondary}>Crear reporte ciudadano ↗</Link></div></section>
      <section className={styles.section}>
        <div className={styles.sectionTitle}><span className={styles.eyebrow}>PREGUNTAS FRECUENTES</span><h2>Antes de empezar.</h2></div>
        <div className={styles.faq}>
          <details><summary>¿Cómo accede mi organización?</summary><p>Ingresá a Acceder y elegí Crear organización. Completá los datos y el teléfono de contacto. Administración general revisa la solicitud y coordina la licencia antes de habilitar el ingreso.</p></details>
          <details><summary>¿Todos los usuarios tienen Admin Core?</summary><p>Admin Core está reservado al rol administrador de la organización y no es un módulo adicional de pago. Operadores y visualizadores conservan los permisos de su rol. Si necesitás corregir el responsable o sus datos, contactá a EcoNexo.</p></details>
          <details><summary>¿Necesito instalar sensores?</summary><p>Podés trabajar con las fuentes meteorológicas, satelitales y comunitarias disponibles. Los nodos IoT incorporan mediciones locales cuando tu organización dispone de equipos y conectividad.</p></details>
          <details><summary>¿Las alertas son confirmaciones oficiales?</summary><p>Son señales para apoyar la evaluación. La confirmación y la respuesta corresponden al equipo responsable y a las autoridades competentes. Consultá la metodología y las limitaciones de cada fuente.</p></details>
        </div>
      </section>
      <section id="contacto" className={styles.contact}><span className={styles.eyebrow}>HABLEMOS DE TU TERRITORIO</span><h2>Una mejor decisión<br />empieza con una conexión.</h2><a className={styles.email} href="mailto:econexoargentina@gmail.com">econexoargentina@gmail.com <span aria-hidden="true">↗</span></a><div className={styles.buttons}><Link href="/login" className={styles.primary}>Acceder a EcoNexo ↗</Link><a href="mailto:econexoargentina@gmail.com?subject=Consulta%20sobre%20EcoNexo" className={styles.secondary}>Contactar al equipo</a></div></section>
    </main>
    <SiteFooter brand={<RegisteredWordmark />} />
  </div>;
}
