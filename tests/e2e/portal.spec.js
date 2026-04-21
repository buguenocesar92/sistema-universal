// tests/e2e/portal.spec.js — Test E2E del portal de upload de Excel
// Requiere: npm install -D @playwright/test
// Correr:   npx playwright test

const { test, expect } = require('@playwright/test');

const PORTAL_URL = process.env.PORTAL_URL || 'https://sistema.kraftdo.cl';
const UPLOAD_TOKEN = process.env.UPLOAD_TOKEN || 'test-token';

test.describe('KraftDo Upload Portal', () => {

  test('página carga correctamente', async ({ page }) => {
    await page.goto(PORTAL_URL);
    await expect(page.locator('h1')).toContainText('KraftDo');
    await expect(page.locator('select#empresa')).toBeVisible();
    await expect(page.locator('input#token')).toBeVisible();
  });

  test('no permite enviar sin archivo', async ({ page }) => {
    await page.goto(PORTAL_URL);
    const btn = page.locator('button#btn');
    await expect(btn).toBeDisabled();
  });

  test('rechaza token inválido', async ({ page }) => {
    await page.goto(PORTAL_URL);
    await page.selectOption('#empresa', 'adille');
    await page.fill('#token', 'token_falso');

    // Crear archivo dummy para poder hacer click
    const fileInput = page.locator('#fileInput');
    await fileInput.setInputFiles({
      name: 'test.xlsx',
      mimeType: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      buffer: Buffer.from('PK\x03\x04dummy excel content')
    });

    await page.click('#btn');
    await expect(page.locator('#status')).toContainText(/error|403|incorrecto/i, {
      timeout: 5000
    });
  });

  test('health endpoint responde', async ({ request }) => {
    const response = await request.get(`${PORTAL_URL}/health`);
    expect(response.status()).toBe(200);
    const body = await response.json();
    expect(body).toHaveProperty('status', 'ok');
    expect(body).toHaveProperty('empresas');
  });
});

test.describe('KraftDo API', () => {
  const API_URL = process.env.API_URL || 'https://api.kraftdo.cl';

  test('/health responde 200', async ({ request }) => {
    const r = await request.get(`${API_URL}/health`);
    expect(r.status()).toBe(200);
  });

  test('/metrics retorna formato Prometheus', async ({ request }) => {
    const r = await request.get(`${API_URL}/metrics`);
    expect(r.status()).toBe(200);
    const body = await r.text();
    expect(body).toContain('kraftdo_empresas');
    expect(body).toContain('# HELP');
  });

  test('/empresas lista las empresas configuradas', async ({ request }) => {
    const r = await request.get(`${API_URL}/empresas`);
    expect(r.status()).toBe(200);
  });
});
