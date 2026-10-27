const { chromium } = require('playwright')
;(async () => {
  const b = await chromium.launch()
  const page = await b.newPage({ viewport: { width: 375, height: 667 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true })
  const base = 'https://web-production-df007d.up.railway.app'
  const routes = [['', 'catalogo'], ['productos?', 'detalle'], ['login', 'auth'], ['carrito', 'carrito'], ['pos', 'pos']]
  let allOk = true
  for (const [r, name] of routes) {
    try { await page.goto(base + '/' + r, { waitUntil: 'networkidle', timeout: 50000 }) } catch {}
    await page.evaluate(() => document.fonts?.ready).catch(() => {})
    await page.waitForTimeout(700)
    const m = await page.evaluate(() => ({
      iw: window.innerWidth,
      sw: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth)
    }))
    const ok = m.sw <= m.iw + 1
    if (!ok) allOk = false
    console.log((ok ? 'PASS' : 'FAIL') + '  ' + name.padEnd(12) + ' innerWidth=' + m.iw + ' scrollWidth=' + m.sw)
    await page.screenshot({ path: 'docs/mobile-evidencia/' + name + '.png' })
  }
  await b.close()
  console.log(allOk ? '== MOVIL RESPONSIVO: OK (sin scroll horizontal) ==' : '== QUEDAN DESBORDES ==')
})().catch(e => { console.error('FATAL', e.message); process.exit(1) })
