const assert = require('node:assert/strict');
const path = require('node:path');
const { chromium } = require(path.resolve(__dirname, '../../node_modules/playwright'));

const web = process.env.E2E_WEB_URL || 'http://127.0.0.1:4200';
const api = process.env.E2E_API_URL || 'http://127.0.0.1:8001/api';
for (const url of [web, api]) {
  assert.equal(new URL(url).hostname, '127.0.0.1', 'Usar solamente servidores locales de demostración.');
}

async function read(url) {
  const response = await fetch(api + url);
  assert.equal(response.status, 200, url);
  return response.json();
}

(async () => {
  const stores = await read('/plataforma/tiendas');
  const fashion = stores.find(store => store.nombre === 'FashionStore Demo');
  const urbana = stores.find(store => store.nombre === 'Moda Urbana Demo');
  assert(fashion && urbana, 'Cargar primero las dos empresas de demostración.');
  const catalogs = new Map();
  const branches = new Map();
  for (const store of [fashion, urbana]) {
    catalogs.set(store.id, await read('/products/?empresa_id=' + store.id));
    branches.set(store.id, await read('/branches/?empresa_id=' + store.id));
    assert(catalogs.get(store.id).length > 0);
    assert(branches.get(store.id).length > 0);
  }

  const browser = await chromium.launch();
  let page;
  try {
    const context = await browser.newContext();
    await context.route('https://**/*', route => route.abort());
    page = await context.newPage();
    page.setDefaultTimeout(60000);
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(web + '/', { waitUntil: 'domcontentloaded' });
    const selector = page.locator('#public-store');
    await selector.waitFor();
    await page.waitForFunction(count => document.querySelectorAll('.product-card').length === count, catalogs.get(fashion.id).length);
    const first = catalogs.get(fashion.id)[0];
    const card = page.locator('.product-card').filter({ has: page.getByRole('heading', { name: first.name, exact: true }) });
    await card.getByRole('button', { name: 'Ver opciones', exact: true }).click();
    await page.locator('.variant-item').first().waitFor();
    assert.match(await page.locator('.variant-list').innerText(), /disponibles/);
    await page.locator('.modal-close').click();

    await selector.selectOption({ label: urbana.nombre });
    await page.waitForFunction(count => document.querySelectorAll('.product-card').length === count, catalogs.get(urbana.id).length);
    await page.getByRole('heading', { name: catalogs.get(urbana.id)[0].name, exact: true }).waitFor();
    await page.goto(web + '/branches', { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(count => document.querySelectorAll('.branch-card').length === count, branches.get(urbana.id).length);
    assert.equal(await selector.locator('option:checked').innerText(), urbana.nombre);
    await selector.selectOption({ label: fashion.nombre });
    await page.waitForFunction(count => document.querySelectorAll('.branch-card').length === count, branches.get(fashion.id).length);
    await page.reload({ waitUntil: 'domcontentloaded' });
    await page.waitForFunction(count => document.querySelectorAll('.branch-card').length === count, branches.get(fashion.id).length);
    assert.equal(await selector.locator('option:checked').innerText(), fashion.nombre);

    await page.goto(web + '/disponibilidad', { waitUntil: 'domcontentloaded' });
    await page.locator('tbody tr').first().waitFor();
    await selector.selectOption({ label: urbana.nombre });
    await page.waitForFunction(() => document.querySelectorAll('tbody tr').length === 1);
    assert.match(await page.locator('tbody').innerText(), /Polera Urbana Exclusiva/);

    await page.goto(web + '/auth', { waitUntil: 'domcontentloaded' });
    await page.locator('input[name="loginEmail"]').fill('admin@fashionstore.com');
    await page.locator('input[name="loginPassword"]').fill('admin123');
    await page.getByRole('button', { name: 'Acceder a mi cuenta', exact: true }).click();
    await page.waitForURL(web + '/');
    await page.getByRole('heading', { name: first.name, exact: true }).first().waitFor();
    assert.equal(await selector.count(), 0, 'La sesión usa automáticamente su empresa.');
    assert.deepEqual(errors, []);
    console.log(JSON.stringify({
      resultado: 'OK',
      fashionstore: { productos: catalogs.get(fashion.id).length, sucursales: branches.get(fashion.id).length },
      moda_urbana: { productos: catalogs.get(urbana.id).length, sucursales: branches.get(urbana.id).length },
      comprobaciones: ['catálogo público', 'variantes y stock', 'cambio de tienda', 'sucursales', 'persistencia de tienda', 'disponibilidad', 'inicio de sesión'],
    }));
  } catch (error) {
    if (page) console.error('Estado de la página:', await page.locator('body').innerText({ timeout: 3000 }).catch(() => 'No disponible'));
    throw error;
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
