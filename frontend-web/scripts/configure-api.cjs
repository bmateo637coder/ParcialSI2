const fs = require('node:fs');
const path = require('node:path');

function apiUrl(value) {
  const configured = (value || '/api').trim().replace(/\/+$/, '');
  if (configured === '/api') return configured;
  let parsed;
  try { parsed = new URL(configured); } catch { throw new Error('FASHIONSTORE_API_URL debe ser una URL HTTPS que termine en /api.'); }
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(parsed.hostname);
  if (parsed.protocol !== 'https:' && !(local && parsed.protocol === 'http:') ||
      parsed.username || parsed.password || parsed.search || parsed.hash || parsed.pathname !== '/api') {
    throw new Error('FASHIONSTORE_API_URL debe usar HTTPS, terminar en /api y no contener credenciales ni parámetros.');
  }
  return configured;
}

if (require.main === module) {
  const localEnv = path.resolve(__dirname, '../.env');
  if (fs.existsSync(localEnv)) process.loadEnvFile(localEnv);
  if (process.env.VERCEL === '1' && !process.env.FASHIONSTORE_API_URL?.trim()) {
    throw new Error('Configura FASHIONSTORE_API_URL con la URL HTTPS de la API antes de desplegar la web.');
  }
  const config = { apiUrl: apiUrl(process.env.FASHIONSTORE_API_URL) };
  if (process.env.VERCEL === '1' && !config.apiUrl.startsWith('https://')) {
    throw new Error('En Vercel, FASHIONSTORE_API_URL debe apuntar a la API publicada con HTTPS.');
  }
  fs.writeFileSync(path.resolve(__dirname, '../public/app-config.js'),
    'globalThis.__FASHIONSTORE_CONFIG__ = ' + JSON.stringify(config).replace(/</g, '\\u003c') + ';\n');
  console.log('Configuración pública del backend preparada.');
}

module.exports = { apiUrl };
