const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require(path.resolve(__dirname, '../../node_modules/playwright'));

const web = process.env.E2E_WEB_URL;
const api = process.env.E2E_API_URL;
if (!web || !api || !api.startsWith('http://127.0.0.1:')) {
  throw new Error('Define E2E_WEB_URL y E2E_API_URL con servidores temporales locales.');
}

async function operations(page) {
  for(let attempt=0;attempt<3;attempt++) {
  try { return await page.evaluate(() => new Promise((resolve, reject) => {
    const request = indexedDB.open('FashionStoreOffline');
    request.onerror = () => reject(request.error);
    request.onsuccess = () => {
      const db = request.result;
      const rows = db.transaction('operaciones').objectStore('operaciones').getAll();
      rows.onsuccess = () => { resolve(rows.result); db.close(); };
      rows.onerror = () => { reject(rows.error); db.close(); };
    };
  })); } catch(error) {
    if(!error.message.includes('Execution context was destroyed') || attempt===2) throw error;
    await page.waitForLoadState('domcontentloaded');
  }
  }
}

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ acceptDownloads: true });
  let offline = false;
  let failSync = true;
  let sentStateObserved = false;
  await context.route(/https?:\/\/[^/]+\/api(?:\/|$)/, async route => {
    if (offline) return route.abort('internetdisconnected');
    const url = new URL(route.request().url());
    if (url.pathname === '/api/sync' && route.request().method() === 'POST') {
      const batch = route.request().postDataJSON().operaciones;
      const stored = await operations(page);
      for (const op of batch) assert.equal(stored.find(row => row.uuid === op.uuid)?.estado, 'ENVIADA');
      sentStateObserved = true;
      if (failSync) return route.fulfill({ status: 503, contentType: 'application/json', body: '{"detail":"Fallo temporal de prueba"}' });
    }
    const response = await route.fetch({ url: api + url.pathname.slice(4) + url.search });
    await route.fulfill({ response });
  });
  const page = await context.newPage();
  page.setDefaultTimeout(25000);
  const errors = [];
  page.on('pageerror', error => errors.push(error.message));
  try {
    await page.goto(web + '/auth');
    await page.locator('input[name="loginEmail"]').fill('admin@fashionstore.com');
    await page.locator('input[name="loginPassword"]').fill('admin123');
    await page.getByRole('button', { name: 'Acceder a mi cuenta', exact: true }).click();
    await page.waitForURL(web + '/');
    await page.goto(web + '/offline/sync');
    await page.getByRole('button', { name: 'Descargar catálogo para trabajar sin conexión', exact: true }).click();
    await page.getByText(/Catálogo, variantes y sucursales guardados/).waitFor();
    await page.evaluate(async () => {
      await Promise.race([navigator.serviceWorker.ready, new Promise((_, reject) => setTimeout(() => reject(new Error('Service worker no instalado')), 45000))]);
    });
    await page.reload();
    await page.waitForFunction(() => Boolean(navigator.serviceWorker.controller));
    offline = true;
    await context.setOffline(true);
    await page.reload();
    await page.getByRole('heading', { name: 'Sincronización Offline', exact: true }).waitFor();
    await page.getByRole('link', { name: 'Caja', exact: true }).click();
    await page.getByRole('heading', { name: 'Caja (POS)', exact: true }).waitFor();
    await page.waitForFunction(() => document.querySelector('select')?.options.length > 1);
    await page.locator('select').first().selectOption({ index: 1 });
    await page.getByRole('button', { name: 'Agregar', exact: true }).click();
    await page.locator('#cash-received').fill('10000');
    await page.getByRole('button', { name: 'Cobrar y registrar venta', exact: true }).click();
    await page.waitForFunction(() => document.querySelector('button.btn-primary.btn-block')?.disabled === true);
    const saved = await operations(page);
    assert.equal(saved.length, 1);
    assert.equal(saved[0].estado, 'REGISTRADA_LOCAL');
    assert.ok(saved[0].empresaId > 0 && saved[0].items[0].precio > 0);
    await page.getByRole('link', { name: 'Reservas', exact: true }).click();
    await page.getByRole('button', { name: 'Nueva reserva (CU13)', exact: true }).click();
    await page.waitForFunction(() => document.querySelectorAll('select')[1]?.options.length > 1);
    await page.locator('select').nth(0).selectOption({ index: 1 });
    await page.locator('select').nth(1).selectOption({ index: 1 });
    await page.waitForFunction(() => document.querySelectorAll('select')[2]?.options.length > 1);
    await page.locator('select').nth(2).selectOption({ index: 1 });
    await page.getByRole('button', { name: 'Agregar prenda', exact: true }).click();
    await page.getByRole('button', { name: 'Confirmar reserva', exact: true }).click();
    await page.waitForFunction(() => new Promise(resolve => {
      const request = indexedDB.open('FashionStoreOffline');
      request.onsuccess = () => {
        const count = request.result.transaction('operaciones').objectStore('operaciones').count();
        count.onsuccess = () => { request.result.close(); resolve(count.result === 2); };
      };
    }));
    await page.getByRole('link', { name: 'Sincronización', exact: true }).click();
    await page.reload();
    assert.equal((await operations(page))[0].uuid, saved[0].uuid);
    console.log('PASS: reinicio sin conexión, catálogo, venta y reserva locales persistentes.');

    offline = false;
    await context.setOffline(false);
    await page.getByRole('button', { name: 'Sincronizar ahora', exact: true }).click();
    await page.getByText('Estado: ENVIADA', { exact: true }).first().waitFor();
    assert.equal((await operations(page)).length, 2);
    assert.ok(sentStateObserved);
    await page.reload();
    await page.getByText('Estado: ENVIADA', { exact: true }).first().waitFor();
    failSync = false;
    await page.getByRole('button', { name: 'Sincronizar ahora', exact: true }).click();
    await page.waitForFunction(() => [...document.querySelectorAll('li')].filter(li => li.textContent.includes('Estado: CONFIRMADA')).length === 2);
    await page.getByRole('button', { name: 'Sincronizar ahora', exact: true }).click();
    const token = await page.evaluate(() => localStorage.getItem('token'));
    const response = await context.request.get(api + '/orders', { headers: { Authorization: 'Bearer ' + token } });
    assert.equal(response.status(), 200);
    assert.equal((await response.json()).length, 1);
    const reservations = await context.request.get(api + '/reservations', { headers: { Authorization: 'Bearer ' + token } });
    assert.equal((await reservations.json()).length, 1);
    console.log('PASS: estado ENVIADA persistente ante errores, reintentos y sincronización sin duplicados.');

    await page.getByRole('link', { name: 'Reportes IA', exact: true }).click();
    await page.getByPlaceholder('Ej: Ventas de septiembre de 2026 por sucursal').fill('ventas de este mes por sucursal');
    await page.getByRole('button', { name: 'Generar reporte', exact: true }).click();
    await page.locator('tbody tr').first().waitFor();
    const downloading = page.waitForEvent('download');
    await page.getByRole('button', { name: 'Exportar PDF', exact: true }).click();
    const download = await downloading;
    assert.match(download.suggestedFilename(), /reporte-\d+\.pdf/);
    assert.equal(await download.failure(), null);
    console.log('PASS: reporte con filas reales y descarga autenticada.');

    await page.getByRole('link', { name: 'Analítica', exact: true }).click();
    await page.getByRole('button', { name: 'Entrenar modelos y actualizar análisis', exact: true }).click();
    await page.getByRole('heading', { name: 'Existencias y demanda estimada', exact: true }).waitFor();
    const scatter = page.getByRole('group', { name: 'Grupos de prendas por precio y existencias', exact: true });
    await scatter.locator('circle').first().waitFor({ state: 'attached' });
    assert.ok(await scatter.locator('circle').count() > 0);
    assert.ok(Number.isFinite(Number(await scatter.locator('circle').first().getAttribute('cx'))));
    await scatter.locator('circle').first().click();
    await page.getByRole('button', { name: 'Cerrar detalle', exact: true }).waitFor();
    await page.getByRole('combobox', { name: 'Sucursal del análisis', exact: true }).selectOption({ index: 1 });
    assert.ok(await scatter.locator('circle').count() > 0);
    console.log('PASS: gráficos ML con datos reales, selección de prendas y filtro por sucursal.');

    await page.getByRole('button', { name: 'Salir', exact: true }).click();
    await page.goto(web + '/auth');
    await page.locator('input[name="loginEmail"]').fill('admin@modaurbana.demo');
    await page.locator('input[name="loginPassword"]').fill('admin123');
    await page.getByRole('button', { name: 'Acceder a mi cuenta', exact: true }).click();
    await page.waitForURL(web + '/');
    await page.getByRole('heading', { name: 'Polera Urbana Exclusiva', exact: true }).first().waitFor();
    await page.goto(web + '/offline/sync');
    await page.getByText('No hay operaciones pendientes', { exact: true }).waitFor();
    assert.equal((await operations(page)).length, 2, 'Las operaciones de la primera empresa deben conservarse');
    assert.deepEqual(errors, []);
    console.log('PASS: cambio de empresa sin mostrar ni enviar operaciones ajenas.');
  } catch (error) {
    console.error('Browser errors:', errors);
    console.error('Page:', page.url(), (await page.locator('body').innerText()).slice(0, 2500));
    throw error;
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
