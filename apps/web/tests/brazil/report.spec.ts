import { expect, test } from '@playwright/test';
import { buildBrazilSoyReport } from '../../components/BrazilSoyPanel';
import { translateBrazil } from '../../app/lib/brazil-translations';

test('el informe respeta el idioma y escapa los datos del productor', () => {
  const report: Parameters<typeof buildBrazilSoyReport>[0] = {
    issued_at: '2026-11-18T12:00:00Z', method: 'br-mt-soja-v2', status: 'datos_insuficientes',
    evidence: {
      name: '<script>alert(1)</script>', lat: -12.5, lon: -55.7, area_ha: 10,
      observed_on: '2026-11-18', sowing_date: null, stage: 'floracion', cultivar: 'Cultivar propio', source: 'Datos pendientes',
      ph: null, soil_temperature_c: null, soil_analysis_ok: null, drainage_ok: null, water_ok: null,
      compaction: null, erosion: null, seed_ok: null, nodulation_plan_ok: null, pests_present: null,
    },
    risks: [], missing: ['Drenaje'], recommendations: [], forecast: [], weather_error: null,
    sources: [], limitations: 'Evidencia declarada por el usuario.',
  };
  const pt = buildBrazilSoyReport(report, text => translateBrazil(text, 'pt'), 'pt-BR');
  expect(pt).toContain('lang="pt-BR"');
  expect(pt).toContain('Relatório de soja');
  expect(pt).toContain('Floração');
  expect(pt).toContain('Drenagem');
  expect(pt).toContain('<td>Datos pendientes</td>'); // User-entered observations must stay original.
  expect(pt).toContain('&lt;script&gt;');
  expect(pt).not.toContain('<script>');
  const es = buildBrazilSoyReport(report, text => translateBrazil(text, 'es'), 'es-AR');
  expect(es).toContain('lang="es"');
  expect(es).toContain('Informe de soja');
});
