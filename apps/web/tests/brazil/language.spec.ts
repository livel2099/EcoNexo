import { expect, test } from '@playwright/test';
import { translateBrazil } from '../../app/lib/brazil-translations';

test('traduce riesgos sin alterar mediciones ni texto desconocido', () => {
  expect(translateBrazil('pH declarado 4.8; fuera del rango bibliográfico orientativo 5,5–7,5.', 'pt')).toBe('pH declarado 4.8; fora da faixa bibliográfica de referência 5,5–7,5.');
  expect(translateBrazil('Nombre propio del productor', 'pt')).toBe('Nombre propio del productor');
  expect(translateBrazil('Datos pendientes', 'es')).toBe('Datos pendientes');
});

test('cambia idioma, conserva el formulario y recuerda la selección', async ({ page }) => {
  await page.goto('/login');
  await page.getByRole('button', { name: 'Ingresar', exact: true }).click();
  await expect(page.getByRole('button', { name: /Abrir Brasil/ })).toBeVisible({ timeout: 30_000 });
  await page.getByRole('button', { name: /Abrir Brasil/ }).click();
  await page.getByRole('button', { name: 'Português', exact: true }).click();
  await expect(page.getByRole('heading', {name:'Laranja e eucalipto: acompanhamento por propriedade'})).toBeVisible();
  await page.getByRole('button', {name:'Soja · previsão e avaliação',exact:true}).click();
  await expect(page.getByRole('heading', { name: 'Previsão para soja · próximos 7 dias' })).toBeVisible();
  await page.getByRole('button', { name: 'Continuar para a avaliação', exact: true }).click();
  await page.getByLabel('Nome do talhão', { exact: true }).fill('Talhão São José');
  await page.getByLabel(/Estádio declarado/).selectOption('floracion');
  await page.getByRole('button', { name: 'Español', exact: true }).click();
  await expect(page.getByLabel('Nombre del lote', { exact: true })).toHaveValue('Talhão São José');
  await expect(page.getByLabel(/Etapa declarada/)).toHaveValue('floracion');
  await page.getByRole('button', { name: 'Português', exact: true }).click();
  await page.getByRole('button', { name: 'Mapa estadual e alertas', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Monitoramento de Mato Grosso' })).toBeVisible();
  await expect(page.getByText('Os alertas reais requerem a API conectada. O modo de demonstração não gera detecções.')).toBeVisible();
  await page.reload();
  await page.getByRole('button', { name: /Abrir Brasil/ }).click();
  await expect(page.getByRole('button', { name: 'Português', exact: true })).toHaveAttribute('aria-pressed', 'true');
  await page.getByRole('button', {name:'Soja · previsão e avaliação',exact:true}).click();
  await expect(page.getByRole('heading', { name: 'Previsão para soja · próximos 7 dias' })).toBeVisible();
});
