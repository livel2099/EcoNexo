import Link from "next/link";
import { LegalSection } from "../../components/LegalPage";
import SiteFooter from "../../components/SiteFooter";

export const metadata = { title: "Documentación y primeros pasos", description: "Guía de acceso, configuración, roles y flujo de trabajo de EcoNexo." };

export default function DocumentationPage() {
  return <div className="legal-page">
    <header className="legal-topbar"><Link href="/" className="brand">ECO<span>NEXO</span></Link><Link href="/login">Acceder →</Link></header>
    <main className="legal-document">
      <div className="legal-cover"><span>GUÍA DE LA PLATAFORMA</span><h1>Documentación y primeros pasos</h1><p>El recorrido de tu organización: del alta al seguimiento de una decisión ambiental.</p></div>
      <div className="legal-content">
    <LegalSection number="01" title="Solicitar acceso">
      <p>En <Link href="/login">Acceder</Link>, elegí Crear organización. Registrá el nombre de la organización, responsable, correo, contraseña, municipio y teléfono de contacto. El alta queda pendiente hasta que administración general coordine la licencia y apruebe el acceso.</p>
      <p>Cuando se habilite tu cuenta, ingresá con el correo registrado. Si recibiste una contraseña temporal, tendrás que cambiarla antes de operar.</p>
    </LegalSection>
    <LegalSection number="02" title="Configurar la organización en Admin Core">
      <p>El administrador encuentra Admin Core en la navegación del Centro de Comando. Desde allí puede gestionar usuarios y roles, datos de la organización, fuentes ambientales, zonas y suscripción. Admin Core no requiere una licencia adicional; los límites y módulos operativos dependen del plan.</p>
      <ul><li><strong>Administrador:</strong> configura el equipo y los recursos de su organización.</li><li><strong>Operador:</strong> trabaja con señales y acciones habilitadas por su rol.</li><li><strong>Visualizador:</strong> consulta información sin permisos administrativos.</li></ul>
      <p>Si no aparece Admin Core, verificá que tu cuenta tenga rol administrador. Administración general puede corregir el rol o los datos de acceso. La consola general de EcoNexo está reservada al equipo autorizado de la plataforma.</p>
    </LegalSection>
    <LegalSection number="03" title="Conectar y verificar fuentes">
      <p>Definí el territorio de trabajo y revisá las fuentes configuradas. Los sensores aportan mediciones locales; las fuentes meteorológicas y satelitales agregan contexto. Comprobá la última actualización, la ubicación, la disponibilidad y si la señal es medida, modelada o reportada.</p>
      <p>Consultá <Link href="/metodologia">Metodología y fuentes</Link> para interpretar los indicadores y sus limitaciones.</p>
    </LegalSection>
    <LegalSection number="04" title="Trabajar con alertas">
      <ol><li>Ubicá la señal en el Centro de Comando y revisá su evidencia.</li><li>Contrastá las fuentes y verificá el evento con el equipo responsable.</li><li>Confirmá, descartá o escalá según los permisos y el protocolo de tu organización.</li><li>Registrá las acciones y revisá la evolución del evento.</li></ol>
      <p>Fuego y humo, sanidad forestal, EcoNexo AG y EcoCampo complementan el análisis cuando están habilitados. Las estimaciones orientan la evaluación y requieren interpretación profesional según el caso.</p>
    </LegalSection>
    <LegalSection number="05" title="Reportes, evidencia e investigación">
      <p>Los <Link href="/reportar">reportes ciudadanos</Link> ingresan con ubicación y pasan por validación. El módulo Informes permite documentar evidencia y metodología. <Link href="/red-investigacion">EcoNexoFoI</Link> ofrece un espacio gratuito de investigación con registro comunitario independiente del alta institucional.</p>
    </LegalSection>
    <LegalSection number="06" title="Licencias y corrección de datos">
      <p>Revisá tu plan y su estado desde Admin Core → Suscripción. Podés solicitar un cambio de alcance. Administración general gestiona activaciones y bajas, corrige nombres, correos y teléfonos y restablece contraseñas mediante una clave temporal.</p>
      <p>Una licencia dada de baja conserva su historial y deshabilita los módulos licenciados. El administrador mantiene acceso a la gestión de su suscripción mientras su cuenta y organización sigan habilitadas.</p>
      <p>Contacto: <a href="mailto:econexoargentina@gmail.com">econexoargentina@gmail.com</a>. Indicá tu organización y el dato que necesitás corregir.</p>
    </LegalSection>
    <p><Link href="/">← Volver al inicio</Link> · <Link href="/login">Acceder a EcoNexo →</Link></p>
      </div>
    </main>
    <SiteFooter />
  </div>;
}
