const { chromium } = require('playwright')
;(async () => {
  const browser = await chromium.launch()
  const page = await browser.newPage({ viewport: { width: 375, height: 667 }, isMobile: true })
  const base = 'https://web-production-df007d.up.railway.app'
  const routes = ['', 'auth', 'branches', 'carrito', 'pos', 'vestidor', 'reservas', 'admin', 'promos', 'provider', 'reports', 'profile']
  for (const r of routes) {
    try { await page.goto(base + '/' + r, { waitUntil: 'networkidle', timeout: 40000 }) } catch (e) {}
    await page.waitForTimeout(800)
    const m = await page.evaluate(() => {
      const vw = document.documentElement.clientWidth
      const vh = document.documentElement.clientHeight
      const bad = []
      document.querySelectorAll('body *').forEach(e => {
        const r = e.getBoundingClientRect()
        if (r.width === 0 && r.height === 0) return
        if (r.right > vw + 1) bad.push({ tag: e.tagName, cls: String(e.className || e.id || '').slice(0, 60), right: Math.round(r.right), left: Math.round(r.left), w: Math.round(r.width) })
      })
      bad.sort((a, b) => b.right - a.right)
      return { vw, scrollW: document.documentElement.scrollWidth, bad: bad.slice(0, 5) }
    }).catch(e => ({ vw: 0, scrollW: 0, bad: [] }))
    const title = await page.title().catch(() => '')
    const over = m.scrollW - m.vw
    console.log((r || 'root').padEnd(33), over > 2 ? 'OVERFLOW+'+over : 'ok       ',
      '| right>viewport:', m.bad.length,
      m.bad.slice(0,2).map(b => b.tag + '.' + b.cls + '(r=' + b.right + ')').join(' | '))
  }
  console.log('=== screenshots ===')
  const shots = [['', 'catalogo'], ['pos', 'pos'], ['vestidor', 'vestidor'], ['reports', 'reports'], ['auth', 'login']]
  for (const [r, name] of shots) {
    try { await page.goto(base + '/' + r) } catch (e) {}
    await page.waitForTimeout(1000)
    await page.screenshot({ path: 'mob-' + name + '.png' })
  }
  await browser.close()
})().catch(e => console.error('FATAL:', e.message))
