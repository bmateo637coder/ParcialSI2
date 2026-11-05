const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const { apiUrl } = require('./configure-api.cjs');

test('permite el proxy local y normaliza una URL publicada', () => {
  assert.equal(apiUrl(), '/api');
  assert.equal(apiUrl(' https://api.example.com/api/ '), 'https://api.example.com/api');
  assert.equal(apiUrl('http://127.0.0.1:8001/api'), 'http://127.0.0.1:8001/api');
  for (const value of ['http://api.example.com/api', 'https://api.example.com',
    'https://demo:private@api.example.com/api', 'https://api.example.com/api?token=private']) {
    assert.throws(() => apiUrl(value));
  }
});

test('el build alojado exige la API HTTPS y solo publica su URL', () => {
  const folder = fs.mkdtempSync(path.join(os.tmpdir(), 'fashionstore-config-'));
  try {
    fs.mkdirSync(path.join(folder, 'scripts'));
    fs.mkdirSync(path.join(folder, 'public'));
    const script = path.join(folder, 'scripts', 'configure-api.cjs');
    fs.copyFileSync(path.join(__dirname, 'configure-api.cjs'), script);
    for (const value of ['', '/api', 'http://localhost:8001/api', 'https://api.example.com/api']) {
      const result = spawnSync(process.execPath, [script], { cwd: folder,
        env: { ...process.env, VERCEL: '1', FASHIONSTORE_API_URL: value, SECRET_KEY: 'must-not-be-public' },
        encoding: 'utf8' });
      assert.equal(result.status, value.startsWith('https://') ? 0 : 1);
    }
    const output = fs.readFileSync(path.join(folder, 'public', 'app-config.js'), 'utf8');
    assert.equal(output, 'globalThis.__FASHIONSTORE_CONFIG__ = {"apiUrl":"https://api.example.com/api"};\n');
  } finally {
    // Carpeta creada por esta prueba, siempre dentro del directorio temporal.
    assert.equal(path.dirname(path.resolve(folder)), path.resolve(os.tmpdir()));
    assert.ok(path.basename(folder).startsWith('fashionstore-config-'));
    fs.rmSync(folder, { recursive: true });
  }
});
