import { LegalPage, LegalSection, legalContact } from "../../components/LegalPage";

export default function AccessibilityPage() {
  return <LegalPage title="Declaración de Accesibilidad" subtitle="Compromiso de diseño inclusivo para operaciones ambientales críticas.">
    <LegalSection number="01" title="Objetivo"><p>EcoNexo busca alinearse progresivamente con WCAG 2.2 nivel AA. La accesibilidad se considera un requisito operativo: alertas, formularios e informes deben comprenderse y utilizarse con distintos dispositivos, capacidades y condiciones de campo.</p></LegalSection>
    <LegalSection number="02" title="Medidas incorporadas"><ul><li>Estructura semántica, etiquetas de formularios y mensajes de error textuales.</li><li>Navegación por teclado y estados de foco visibles.</li><li>Contraste alto, información que no depende únicamente del color y soporte de movimiento reducido.</li><li>Diseño adaptable, controles táctiles y documentos imprimibles.</li><li>Idioma declarado y textos claros en español de Argentina.</li></ul></LegalSection>
    <LegalSection number="03" title="Trabajo pendiente"><p>Antes de producción se requiere auditoría manual con lectores de pantalla, pruebas de teclado, contraste, zoom 200–400%, reflow, formularios, mapas y PDF exportados. Los mapas interactivos deberán ofrecer alternativas textuales equivalentes para alertas y coordenadas.</p></LegalSection>
    <LegalSection number="04" title="Contacto"><p>Para informar una barrera, indicar página, dispositivo, navegador, tecnología de asistencia y resultado esperado a <strong>{legalContact}</strong>. Se priorizarán impedimentos que afecten tareas críticas.</p></LegalSection>
  </LegalPage>;
}
